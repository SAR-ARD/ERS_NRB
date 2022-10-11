import os
import re
from math import isclose
from datetime import datetime
import numpy as np
from pyroSAR import identify
from pyroSAR.ERS.mapping import ANGLES_RESOLUTION
from spatialist import Raster
from spatialist.ancillary import finder
from spatialist.vector import wkt2vector, bbox
from spatialist.raster import rasterize
from ERS_NRB.metadata.mapping import NRB_PATTERN, ORB_MAP, NOISE_MAP


def get_prod_meta(product_id, tif, src_scenes):
    """
    Returns a metadata dictionary, which is generated from the ID of a product scene using a regular expression pattern
    and from a measurement GeoTIFF file of the same product scene using spatialist's Raster class.
    
    Parameters
    ----------
    product_id: str
        The product ID (filename) of the product scene.
    tif: str
        The paths to a measurement GeoTIFF file of the product scene.
    src_scenes: list[str]
        A list of paths pointing to the source scenes of the product.
    Returns
    -------
    dict
        A dictionary containing metadata for the product scene.
    """
    out = re.match(re.compile(NRB_PATTERN), product_id).groupdict()
    coord_list = [identify(src).meta['coordinates'] for src in src_scenes]
    if tif:
        with vec_from_srccoords(coord_list=coord_list) as srcvec:
            with Raster(tif) as ras:
                image = ras.raster.GetGeoTransform()
                vec = ras.bbox()
                srs = vec.srs
                out['extent'] = vec.extent
                out['wkt'] = srs.ExportToWkt()
                out['epsg'] = vec.getProjection(type='epsg')
                out['rowSpacing'] = image[5]
                out['columnSpacing'] = image[1]
                out['rows'] = ras.rows
                out['cols'] = ras.cols
                out['res'] = ras.res
                geo = ras.geo
                out['transform'] = [geo['xres'], geo['rotation_x'], geo['xmin'],
                                    geo['rotation_y'], geo['yres'], geo['ymax']]
                
                vec.reproject(4326)
                feat = vec.getFeatureByIndex(0)
                geom = feat.GetGeometryRef()
                point = geom.Centroid()
                out['wkt_pt'] = point.ExportToWkt()
                out['wkt_env'] = vec.convert2wkt(set3D=False)[0]
                out['extent_4326'] = vec.extent
                
                # Calculate number of nodata border pixels based on source scene(s) footprint
                ras_srcvec = rasterize(vectorobject=srcvec, reference=ras, burn_values=[1])
                arr_srcvec = ras_srcvec.array()
                out['nodata_borderpx'] = np.count_nonzero(np.isnan(arr_srcvec))
            srcvec = None
    
    return out


def get_uid_sid(filepath):
    """
    Returns the unique identifier of a Sentinel-1 scene and a pyroSAR metadata handler generated using 
    `pyroSAR.drivers.identify`
    
    Parameters
    ----------
    filepath: str
        Filepath pointing to a Sentinel-1 scene.
    
    Returns
    -------
    uid: str
        The last four characters of a Sentinel-1 filename, which is the unique identifier of the scene.
    sid: pyroSAR.drivers.ID subclass object
        A pyroSAR metadata handler for the scene generated with `pyroSAR.drivers.identify`.
    """
    
    uid = os.path.basename(filepath).split('.')[0][-4:]
    sid = identify(filepath)
    
    return uid, sid


def convert_id_coordinates(coords, stac=False):
    """
    Converts a list of coordinate pairs as retrieved by pyroSAR's identify function to either envelop and center for
    usage in the XML metadata files or bbox and geometry for usage in STAC metadata files. The latter is returned if the
    optional parameter 'stac' is set to True, else the former is returned.
    
    Parameters
    ----------
    coords: list[tuple(float, float)]
        List of coordinate pairs as retrieved by `pyroSAR.drivers.identify` from source scenes
    stac: bool, optional
        If set to True, bbox and geometry are returned for usage in STAC Items. If set to False (default) envelop and
        center are returned for usage in XML metadata files.
    
    Returns
    -------
    envelop: str
        Acquisition footprint coordinates for the XML field 'multiExtentOf' in 'eop:Footprint'
    center: str
        Acquisition center coordinates for the XML field 'centerOf' in 'eop:Footprint'
    
    Notes
    -------
    If stac=True the following parameters are returned instead of envelop and center:
    
    bbox: list[float]
        Acquisition bounding box for usage in STAC Items. Formatted in accordance with RFC 7946, section 5:
        https://datatracker.ietf.org/doc/html/rfc7946#section-5
    geometry: GeoJSON Geometry Object
        Acquisition footprint geometry for usage in STAC Items. Formatted in accordance with RFC 7946, section 3.1.:
        https://datatracker.ietf.org/doc/html/rfc7946#section-3.1
    """
    c = coords
    
    lat = [c[0][1], c[1][1], c[2][1], c[3][1]]
    lon = [c[0][0], c[1][0], c[2][0], c[3][0]]
    envelop = '{} {},{} {},{} {},{} {},{} {}'.format(lon[0], lat[0],
                                                     lon[1], lat[1],
                                                     lon[2], lat[2],
                                                     lon[3], lat[3],
                                                     lon[0], lat[0])
    
    lon_c = (max(lon) + min(lon)) / 2
    lat_c = (max(lat) + min(lat)) / 2
    center = '{} {}'.format(lon_c, lat_c)
    
    if stac:
        bbox = [min(lon), min(lat), max(lon), max(lat)]
        geometry = {'type': 'Polygon', 'coordinates': (((lon[0], lat[0]),
                                                        (lon[1], lat[1]),
                                                        (lon[2], lat[2]),
                                                        (lon[3], lat[3]),
                                                        (lon[0], lat[0])),)}
        return bbox, geometry
    else:
        return envelop, center


def convert_spatialist_extent(extent):
    """
    Converts the extent of a spatialist vector object to bbox and geometry as required for the usage in STAC Items:
    https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md#item-fields
    
    Parameters
    ----------
    extent: dict
        The extent of a vector object as returned by `spatialist.vector.Vector.extent`
    
    Returns
    -------
    bbox: list[float]
        Formatted in accordance with RFC 7946, section 5: https://datatracker.ietf.org/doc/html/rfc7946#section-5
    geometry: GeoJSON Geometry Object
        Formatted in accordance with RFC 7946, section 3.1.: https://datatracker.ietf.org/doc/html/rfc7946#section-3.1
    """
    xmin = extent['xmin']
    xmax = extent['xmax']
    ymin = extent['ymin']
    ymax = extent['ymax']
    
    bbox = [xmin, ymin, xmax, ymax]
    geometry = {'type': 'Polygon', 'coordinates': (((xmin, ymin),
                                                    (xmin, ymax),
                                                    (xmax, ymax),
                                                    (xmax, ymin),
                                                    (xmin, ymin)),)}
    
    return bbox, geometry


def vec_from_srccoords(coord_list):
    """
    Creates a single `spatialist.vector.Vector` object from a list of footprint coordinates of source scenes.
    
    Parameters
    ----------
    coord_list: list[list[tuple(float, float)]]
        List containing (for n source scenes) a list of coordinate pairs as retrieved by `pyroSAR.drivers.identify`
    
    Returns
    -------
    `spatialist.vector.Vector` object
    """
    if len(coord_list) == 2:
        if isclose(coord_list[0][0][0], coord_list[1][3][0], abs_tol=0.1):
            c1 = coord_list[1]
            c2 = coord_list[0]
        elif isclose(coord_list[1][0][0], coord_list[0][3][0], abs_tol=0.1):
            c1 = coord_list[0]
            c2 = coord_list[1]
        else:
            RuntimeError('not able to find joined border of source scene footprints '
                         '\n{} and \n{}'.format(coord_list[0], coord_list[1]))
        
        c1_lat = [c1[0][1], c1[1][1], c1[2][1], c1[3][1]]
        c1_lon = [c1[0][0], c1[1][0], c1[2][0], c1[3][0]]
        c2_lat = [c2[0][1], c2[1][1], c2[2][1], c2[3][1]]
        c2_lon = [c2[0][0], c2[1][0], c2[2][0], c2[3][0]]
        
        wkt = 'POLYGON (({} {},{} {},{} {},{} {},{} {}))'.format(c1_lon[0], c1_lat[0],
                                                                 c1_lon[1], c1_lat[1],
                                                                 c2_lon[2], c2_lat[2],
                                                                 c2_lon[3], c2_lat[3],
                                                                 c1_lon[0], c1_lat[0])
    else:  # len(coord_list) == 1
        c = coord_list[0]
        print (c)
        lat = [c[0][1], c[1][1], c[2][1], c[3][1]]
        lon = [c[0][0], c[1][0], c[2][0], c[3][0]]
        
        wkt = 'POLYGON (({} {},{} {},{} {},{} {},{} {}))'.format(lon[0], lat[0],
                                                                 lon[1], lat[1],
                                                                 lon[2], lat[2],
                                                                 lon[3], lat[3],
                                                                 lon[0], lat[0])
    
    return wkt2vector(wkt, srs=4326)


def calc_performance_estimates(files, ref_tif):
    """
    Calculates the performance estimates specified in CARD4L NRB 1.6.9 for all noise power images for the current
    MGRS tile.
    
    Parameters
    ----------
    files: list[str]
        List of paths pointing to the noise power images the estimates should be calculated for.
    ref_tif: str
        A path pointing to a product GeoTIFF file, which is used to get spatial information about the current MGRS tile.
    
    Returns
    -------
    out: dict
        Dictionary containing the calculated estimates for each available polarization.
    """
    out = {}
    with Raster(ref_tif) as ref:
        ext = ref.extent
        epsg = ref.epsg
    
    for f in files:
        pol = re.search('[VH]{2}', f).group().upper()
        with bbox(ext, crs=epsg) as vec:
            with Raster(f)[vec] as ras:
                arr = ras.array()
                # The following need to be of type float, not numpy.float32 in order to be JSON serializable.
                _min = float(np.nanmin(arr))
                _max = float(np.nanmax(arr))
                _mean = float(np.nanmean(arr))
                _stdev = float(np.nanstd(arr))
                _var = float(np.nanvar(arr))
                del arr
        out[pol] = {'minimum': _min,
                    'maximum': _max,
                    'mean': _mean,
                    'stddev': _stdev,
                    'variance': _var}
    return out


def meta_dict(config, target, src_scenes, src_files, proc_time):
    """
    Creates a dictionary containing metadata for a product scene, as well as its source scenes. The dictionary can then
    be utilized by `metadata.xmlparser` and `metadata.stacparser` to generate XML and STAC JSON metadata files,
    respectively.
    
    Parameters
    ----------
    config: dict
        Dictionary of the parsed config parameters for the current process.
    target: str
        A path pointing to the root directory of a product scene.
    src_scenes: list[str]
        A list of paths pointing to the source scenes of the product.
    src_files: list[str]
        A list of paths pointing to the SNAP processed datasets of the product.
    proc_time: datetime.datetime
        The datetime object used to generate the unique product identifier from.
    
    Returns
    -------
    meta: dict
        A dictionary containing an extensive collection of metadata for product as well as source scenes.
    """
    
    meta = {'prod': {},
            'source': {},
            'common': {}}
    
    product_id = os.path.basename(target)
    tif = finder(target, ['[hv]{2}-g-lin.tif$'], regex=True)[0]
    prod_meta = get_prod_meta(product_id=product_id, tif=tif, src_scenes=src_scenes)
    
    src_sid = {}
    for i in range(len(src_scenes)):
        uid, sid = get_uid_sid(filepath=src_scenes[i])
        src_sid[uid] = sid
    
    src0 = list(src_sid.keys())[0]  # first key/first file
    sid0 = src_sid[src0]
    # manifest0 = src_xml[src0]['manifest']
    # nsmap0 = src_xml[src0]['manifest'].nsmap
    
    stac_bbox_4326, stac_geometry_4326 = convert_spatialist_extent(extent=prod_meta['extent_4326'])
    stac_bbox_native = convert_spatialist_extent(extent=prod_meta['extent'])[0]
    
    dem_map = {'GETASSE30': {'url': 'https://step.esa.int/auxdata/dem/GETASSE30',
                             'ref': 'https://seadas.gsfc.nasa.gov/help-8.1.0/desktop/GETASSE30ElevationModel.html',
                             'type': 'elevation',
                             'egm': 'https://apps.dtic.mil/sti/citations/ADA166519'},
               'Copernicus 10m EEA DEM': {'url': 'ftps://cdsdata.copernicus.eu/DEM-datasets/COP-DEM_EEA-10-DGED/2021_1',
                                          'ref': 'https://spacedata.copernicus.eu/web/cscda/dataset-details?articleId=394198',
                                          'type': 'surface',
                                          'egm': 'https://doi.org/10.1029/2011JB008916'},
               'Copernicus 30m Global DEM II': {'url': 'ftps://cdsdata.copernicus.eu/DEM-datasets/COP-DEM_GLO-30-DGED/2021_1',
                                                'ref': 'https://spacedata.copernicus.eu/web/cscda/dataset-details?articleId=394198',
                                                'type': 'surface',
                                                'egm': 'https://doi.org/10.1029/2011JB008916'},
               'Copernicus 90m Global DEM II': {'url': 'ftps://cdsdata.copernicus.eu/DEM-datasets/COP-DEM_GLO-90-DGED/2021_1',
                                                'ref': 'https://spacedata.copernicus.eu/web/cscda/dataset-details?articleId=394198',
                                                'type': 'surface',
                                                'egm': 'https://doi.org/10.1029/2011JB008916'}
               }
    dem_name = config['dem_type']
    dem_url = dem_map[dem_name]['url']
    dem_ref = dem_map[dem_name]['ref']
    dem_type = dem_map[dem_name]['type']
    dem_egm = dem_map[dem_name]['egm']
    
    # Common metadata (sorted alphabetically)
    meta['common']['antennaLookDirection'] = 'RIGHT'
    meta['common']['operationalMode'] = sid0.acquisition_mode
    meta['common']['orbitMeanAltitude'] = '{:.2e}'.format(693000)
    meta['common']['orbitNumbers_abs'] = sid0.orbitNumber_abs
    meta['common']['orbitNumbers_rel'] = sid0.orbitNumber_rel
    meta['common']['orbit'] = {'A': 'ascending', 'D': 'descending'}[sid0.orbit]
    meta['common']['platformFullname'] = {'ERS1': 'ERS1', 'ERS2': 'ERS2', 'ASAR': 'ENVISAT'}[sid0.sensor]    
    meta['common']['instrumentShortName'] = {'ERS1': 'AMI', 'ERS2': 'AMI', 'ASAR': 'ASAR'}[sid0.sensor]
    meta['common']['platformReference'] = {'ERS1': 'http://database.eohandbook.com/database/missionsummary.aspx?missionID=220',
                                           'ERS2': 'http://database.eohandbook.com/database/missionsummary.aspx?missionID=221',
                                           'ENVISAT': 'http://database.eohandbook.com/database/missionsummary.aspx?missionID=2'}[meta['common']['platformFullname']]
    meta['common']['polarisationChannels'] = sid0.polarizations
    meta['common']['polarisationMode'] = prod_meta['pols']
    meta['common']['radarBand'] = 'C'
    meta['common']['radarCenterFreq'] = '{:.3e}'.format(5300000000)
    meta['common']['sensorType'] = 'RADAR'
    
    # Product metadata (sorted alphabetically)
    meta['prod']['access'] = None
    meta['prod']['acquisitionType'] = 'NOMINAL'
    meta['prod']['backscatterConvention'] = 'linear power'
    meta['prod']['backscatterConversionEq'] = '10*log10(DN)'
    meta['prod']['backscatterMeasurement'] = 'gamma0'
    meta['prod']['card4l-link'] = 'https://ceos.org/ard/files/PFS/NRB/v5.5/CARD4L-PFS_NRB_v5.5.pdf'
    meta['prod']['card4l-name'] = 'NRB'
    meta['prod']['card4l-version'] = '5.5'
    meta['prod']['crsEPSG'] = str(prod_meta['epsg'])
    meta['prod']['crsWKT'] = prod_meta['wkt']
    meta['prod']['demEgmReference'] = dem_egm
    meta['prod']['demEgmResamplingMethod'] = 'bilinear'
    meta['prod']['demName'] = dem_name
    meta['prod']['demReference'] = dem_ref
    meta['prod']['demResamplingMethod'] = 'bilinear'
    meta['prod']['demType'] = dem_type
    meta['prod']['demURL'] = dem_url
    meta['prod']['doi'] = None
    meta['prod']['ancillaryData1'] = meta['prod']['demReference']
    meta['prod']['ellipsoidalHeight'] = None
    meta['prod']['fileBitsPerSample'] = '32'
    meta['prod']['fileByteOrder'] = 'little-endian'
    meta['prod']['fileDataType'] = 'float'
    meta['prod']['fileFormat'] = 'COG'
    meta['prod']['filterApplied'] = False
    meta['prod']['filterType'] = None
    meta['prod']['filterWindowSizeCol'] = None
    meta['prod']['filterWindowSizeLine'] = None
    meta['prod']['geoCorrAccuracyAzimuthBias'] = '0'
    meta['prod']['geoCorrAccuracyAzimuthSTDev'] = ANGLES_RESOLUTION[sid0.sensor][sid0.acquisition_mode]['std_dev']
    meta['prod']['geoCorrAccuracyRangeBias'] = '0'
    meta['prod']['geoCorrAccuracyRangeSTDev'] = ANGLES_RESOLUTION[sid0.sensor][sid0.acquisition_mode]['std_dev']
    meta['prod']['geoCorrAccuracy_rRMSE'] = None
    meta['prod']['geoCorrAccuracyReference'] = 'TBD'
    meta['prod']['geoCorrAccuracyType'] = 'slant-range'
    meta['prod']['geoCorrAlgorithm'] = 'TBD'
    meta['prod']['geoCorrResamplingMethod'] = 'bilinear'
    meta['prod']['geom_stac_bbox_native'] = stac_bbox_native
    meta['prod']['geom_stac_bbox_4326'] = stac_bbox_4326
    meta['prod']['geom_stac_geometry_4326'] = stac_geometry_4326
    meta['prod']['geom_xml_center'] = re.search(r'\(([-*0-9 .,]+)\)', prod_meta['wkt_pt']).group(1)
    meta['prod']['geom_xml_envelope'] = re.search(r'\(([-*0-9 .,]+)\)', prod_meta['wkt_env']).group(1)
    meta['prod']['griddingConventionURL'] = 'http://www.mgrs-data.org/data/documents/nga_mgrs_doc.pdf'
    meta['prod']['griddingConvention'] = 'Military Grid Reference System (MGRS)'
    meta['prod']['licence'] = None
    meta['prod']['majorCycleID'] = str(sid0.meta['cycleNumber'])
    meta['prod']['azimuthNumberOfLooks'] = sid0.meta['SPH_AZIMUTH_LOOKS']
    meta['prod']['rangeNumberOfLooks'] = sid0.meta['SPH_RANGE_LOOKS']
    meta['prod']['noiseRemovalApplied'] = NOISE_MAP[sid0.acquisition_mode]
    # meta['prod']['noiseRemovalAlgorithm'] = 'https://doi.org/10.1109/tgrs.2018.2889381'

    meta['prod']['numberLines'] = str(prod_meta['rows'])
    meta['prod']['numberOfAcquisitions'] = str(len(src_scenes))
    meta['prod']['numBorderPixels'] = prod_meta['nodata_borderpx']
    meta['prod']['numPixelsPerLine'] = str(prod_meta['cols'])
    meta['prod']['columnSpacing'] = prod_meta['columnSpacing']
    meta['prod']['rowSpacing'] = prod_meta['rowSpacing']
    meta['prod']['pixelCoordinateConvention'] = 'pixel ULC'
    meta['prod']['processingCenter'] = 'TBD'
    meta['prod']['location'] = 'TBD'
    meta['prod']['processingLevel'] = 'Level 2'
    meta['prod']['processingMode'] = 'PROTOTYPE'
    meta['prod']['processorName'] = 'ERS_NRB'
    meta['prod']['processorVersion'] = 'TBD'
    meta['prod']['productName'] = 'NORMALISED RADAR BACKSCATTER'
    meta['prod']['pxSpacingColumn'] = str(prod_meta['res'][0])
    meta['prod']['pxSpacingRow'] = str(prod_meta['res'][1])
    meta['prod']['radiometricAccuracyAbsolute'] = None
    meta['prod']['radiometricAccuracyRelative'] = None
    meta['prod']['radiometricAccuracyReference'] = None
    meta['prod']['RTCAlgorithm'] = 'https://doi.org/10.1109/Tgrs.2011.2120616'
    meta['prod']['status'] = 'PROTOTYPE'
    meta['prod']['timeCreated'] = datetime.strptime(proc_time.strftime('%Y%m%dT%H%M%S'), '%Y%m%dT%H%M%S')
    meta['prod']['timeStart'] = datetime.strptime(prod_meta['start'], '%Y%m%dT%H%M%S')
    meta['prod']['timeStop'] = datetime.strptime(prod_meta['stop'], '%Y%m%dT%H%M%S')
    meta['prod']['transform'] = prod_meta['transform']
    meta['prod']['wrsLongitudeGrid'] = str(meta['common']['orbitNumbers_rel'])
    
    # Source metadata
    for uid in list(src_sid.keys()):
        coords = src_sid[uid].meta['coordinates']
        xml_envelop, xml_center = convert_id_coordinates(coords=coords)
        stac_bbox, stac_geometry = convert_id_coordinates(coords=coords, stac=True)
        meta['source'][uid] = {}       
        meta['source'][uid]['access'] = 'https://esar-ds.eo.esa.int/oads/access/collection'
        meta['source'][uid]['acquisitionType'] = 'NOMINAL'
        meta['source'][uid]['azimuthNumberOfLooks'] = src_sid[uid].meta['SPH_AZIMUTH_LOOKS']
        meta['source'][uid]['azimuthPixelSpacing'] = src_sid[uid].meta['SPH_AZIMUTH_SPACING']
        meta['source'][uid]['rangeNumberOfLooks'] = src_sid[uid].meta['SPH_RANGE_LOOKS']
        meta['source'][uid]['rangePixelSpacing'] = src_sid[uid].meta['SPH_RANGE_SPACING']
        meta['source'][uid]['azimuthResolution'] = src_sid[uid].meta['azimuthResolution']
        meta['source'][uid]['dataGeometry'] = src_sid[uid].meta['image_geometry']
        meta['source'][uid]['doi'] = 'TBD'
        meta['source'][uid]['faradayMeanRotationAngle'] = None
        meta['source'][uid]['faradayRotationReference'] = None
        meta['source'][uid]['filename'] = src_sid[uid].file
        meta['source'][uid]['geom_stac_bbox_4326'] = stac_bbox
        meta['source'][uid]['geom_stac_geometry_4326'] = stac_geometry
        meta['source'][uid]['geom_xml_center'] = xml_center
        meta['source'][uid]['geom_xml_envelop'] = xml_envelop
        meta['source'][uid]['ionosphereIndicator'] = None
        meta['source'][uid]['orbitStateVector'] = src_sid[uid].meta['DS_ORBIT_STATE_VECTOR_1________NAME'] # Can it be more than one vector? check
        meta['source'][uid]['orbitDataSource'] = ORB_MAP[src_sid[uid].meta['MPH_VECTOR_SOURCE']]
        meta['source'][uid]['orbitDataAccess'] = 'https://scihub.copernicus.eu/gnss'
        np_files = [f for f in src_files if re.search('_NE[BGS]Z', f) is not None]
        meta['source'][uid]['perfEstimates'] = calc_performance_estimates(files=np_files, ref_tif=tif)
        meta['source'][uid]['perfEquivalentNumberOfLooks'] = None
        meta['source'][uid]['perfIntegratedSideLobeRatio'] = None
        meta['source'][uid]['perfNoiseEquivalentIntensityType'] = 'gamma0'
        meta['source'][uid]['perfPeakSideLobeRatio'] = None
        meta['source'][uid]['polCalMatrices'] = None
        meta['source'][uid]['processingCenter'] = src_sid[uid].meta['MPH_PROC_CENTER']
        meta['source'][uid]['processingDate'] = datetime.strptime(src_sid[uid].meta['MPH_PROC_TIME'], '%Y%m%dT%H%M%S')
        meta['source'][uid]['processingLevel'] = 'Level 1'
        try :
            meta['source'][uid]['processorName'] = src_sid[uid].meta['MPH_SOFTWARE_VER'].split('/')[0]
            meta['source'][uid]['processorVersion'] = src_sid[uid].meta['MPH_SOFTWARE_VER'].split('/')[1]
        except:
            meta['source'][uid]['processorName'] = 'Not found'
            meta['source'][uid]['processorVersion'] = 'n/a'
        meta['source'][uid]['productType'] = src_sid[uid].meta['product']
        meta['source'][uid]['lineLength'] = src_sid[uid].meta['SPH_LINE_LENGTH']        
        meta['source'][uid]['lineTimeInterval'] = src_sid[uid].meta['SPH_LINE_TIME_INTERVAL']
        meta['source'][uid]['rangeResolution'] = src_sid[uid].meta['rangeResolution']
        meta['source'][uid]['sensorCalibration'] = 'TBD'
        meta['source'][uid]['status'] = 'ARCHIVED'
        meta['source'][uid]['timeStart'] = datetime.strptime(src_sid[uid].start, '%Y%m%dT%H%M%S')
        meta['source'][uid]['timeStop'] = datetime.strptime(src_sid[uid].stop, '%Y%m%dT%H%M%S')
        meta['source'][uid]['swathIdentifier'] = src_sid[uid].meta['SPH_SWATH']
        meta['source'][uid]['incidenceAngleMax'] = src_sid[uid].meta['incidenceAngleMax']
        meta['source'][uid]['incidenceAngleMin'] = src_sid[uid].meta['incidenceAngleMin']
        meta['source'][uid]['neszNear'] = src_sid[uid].meta['neszNear']
        meta['source'][uid]['neszFar'] = src_sid[uid].meta['neszFar']
        meta['source'][uid]['incidenceAngleMidSwath'] =  src_sid[uid].meta['incidence']
    return meta
