import os
import re
from copy import deepcopy
from datetime import datetime
from matplotlib import dates
import pystac
from pystac.extensions.sar import SarExtension, FrequencyBand, Polarization, ObservationDirection
from pystac.extensions.sat import SatExtension, OrbitState
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from spatialist import Raster
from ERS_NRB.metadata.mapping import SAMPLE_MAP


def product_json(meta, target, tifs):
    """
    Function to generate product-level metadata for an NRB target product in STAC compliant JSON format.
    
    Parameters
    ----------
    meta: dict
        Metadata dictionary generated with `metadata.extract.meta_dict`
    target: str
        A path pointing to the root directory of a product scene.
    tifs: list[str]
        List of paths to all GeoTIFF files of the currently processed NRB product.
    
    Returns
    -------
    None
    """
    scene_id = os.path.basename(target)
    outname = os.path.join(target, '{}.json'.format(scene_id))
    
    start = meta['prod']['timeStart']
    stop = meta['prod']['timeStop']
    date = start + (stop - start)/2
    
    item = pystac.Item(id=scene_id,
                        geometry=meta['prod']['geom_stac_geometry_4326'],
                        bbox=meta['prod']['geom_stac_bbox_4326'],
                        datetime=date,                    
                        properties={})    
    item.common_metadata.start_datetime = start
    item.common_metadata.end_datetime = stop
    item.common_metadata.created = meta['prod']['timeCreated']
    item.common_metadata.instruments = [meta['common']['instrumentShortName']]
    item.common_metadata.platform = meta['common']['platformFullname']
    
    SarExtension.add_to(item)
    SatExtension.add_to(item)
    ProjectionExtension.add_to(item)
    sar_ext = SarExtension.ext(item)
    sat_ext = SatExtension.ext(item)
    proj_ext = ProjectionExtension.ext(item)
    item.stac_extensions.append('https://stac-extensions.github.io/processing/v1.1.0/schema.json')
    item.stac_extensions.append('https://stac-extensions.github.io/card4l/v1.0.0/sar/product.json')
    item.stac_extensions.append('https://stac-extensions.github.io/raster/v1.1.0/schema.json')
    item.stac_extensions.append('https://stac-extensions.github.io/file/v2.0.0/schema.json')
    
    sar_ext.apply(instrument_mode=meta['common']['operationalMode'],
                  frequency_band=FrequencyBand[meta['common']['radarBand'].upper()],
                  polarizations=[Polarization[pol] for pol in meta['common']['polarisationChannels']],
                  product_type=meta['prod']['card4l-name'])
    
    sat_ext.apply(orbit_state=OrbitState[meta['common']['orbit'].upper()],
                  relative_orbit=meta['common']['orbitNumbers_rel'],
                  absolute_orbit=meta['common']['orbitNumbers_abs'])
    
    proj_ext.apply(epsg=int(meta['prod']['crsEPSG']),
                   wkt2=meta['prod']['crsWKT'],
                   bbox=meta['prod']['geom_stac_bbox_native'],
                   shape=[int(meta['prod']['numPixelsPerLine']), int(meta['prod']['numberLines'])],
                   transform=meta['prod']['transform'])

    item.properties['processing:location'] = meta['prod']['location']
    item.properties['processing:facility'] = meta['prod']['processingCenter']
    item.properties['processing:software'] = {meta['prod']['processorName']: meta['prod']['processorVersion']}
    item.properties['processing:level'] = meta['prod']['processingLevel']    
    item.properties['card4l:specification'] = meta['prod']['card4l-name']
    item.properties['card4l:specification_version'] = meta['prod']['card4l-version']
    item.properties['card4l:measurement_type'] = meta['prod']['backscatterMeasurement']
    item.properties['card4l:measurement_convention'] = meta['prod']['backscatterConvention']
    item.properties['card4l:pixel_coordinate_convention'] = {'pixel center': 'center',
                                                             'pixel ULC': 'upper-left',
                                                             'pixel LLC': 'lower-left'
                                                             }[meta['prod']['pixelCoordinateConvention']]
    if meta['prod']['filterApplied']:
        item.properties['card4l:speckle_filtering'] = {'type': meta['prod']['filterType'],
                                                       'window_size_col': meta['prod']['filterWindowSizeCol'],
                                                       'window_size_line': meta['prod']['filterWindowSizeLine']}
    else:
        item.properties['card4l:speckle_filtering'] = "No"
    item.properties['card4l:noise_removal_applied'] = meta['prod']['noiseRemovalApplied']
    item.properties['card4l:conversion_eq'] = meta['prod']['backscatterConversionEq']
    item.properties['card4l:relative_radiometric_accuracy'] = meta['prod']['radiometricAccuracyRelative']
    item.properties['card4l:absolute_radiometric_accuracy'] = meta['prod']['radiometricAccuracyAbsolute']
    item.properties['card4l:resampling_method'] = meta['prod']['geoCorrResamplingMethod']
    item.properties['card4l:dem_resampling_method'] = meta['prod']['demResamplingMethod']
    item.properties['card4l:egm_resampling_method'] = meta['prod']['demEgmResamplingMethod']
    item.properties['card4l:geometric_accuracy_type'] = meta['prod']['geoCorrAccuracyType']
    item.properties['card4l:column_spacing'] = meta['prod']['columnSpacing']
    item.properties['card4l:row_spacing'] = meta['prod']['rowSpacing']    
    for x in ['Azimuth', 'Range']:
        key = ['geoCorrAccuracy{}{}'.format(x, y) for y in ['STDev', 'Bias']]
        stddev = float(meta['prod'][key[0]]) if meta['prod'][key[0]] is not None else None
        bias = float(meta['prod'][key[1]]) if meta['prod'][key[1]] is not None else None
        item.properties['card4l:{}_geometric_accuracy'.format(x.lower())] = {'bias': bias,
                                                                             'stddev': stddev}
    item.properties['card4l:geometric_accuracy_radial_rmse'] = meta['prod']['geoCorrAccuracy_rRMSE']
    
    item.add_link(link=pystac.Link(rel='card4l-document',
                                       target=meta['prod']['card4l-link'].replace('.pdf', '.docx'),
                                       media_type='application/vnd.openxmlformats-officedocument.wordprocessingml'
                                                  '.document',
                                       title='CARD4L Product Family Specification v{}: Normalised Radar Backscatter'
                                             ''.format(meta['prod']['card4l-version'])))
    item.add_link(link=pystac.Link(rel='card4l-document',
                                       target=meta['prod']['card4l-link'],
                                       media_type='application/pdf',
                                       title='CARD4L Product Family Specification v{}: Normalised Radar Backscatter'
                                             ''.format(meta['prod']['card4l-version'])))
    for src in list(meta['source'].keys()):
        src_target = os.path.join('./source',
                                  '{}.json'.format(
                                      os.path.basename(meta['source'][src]['filename']).split('.')[0])).replace('\\',
                                                                                                                '/')
        item.add_link(link=pystac.Link(rel='derived_from',
                                       target=src_target,
                                       media_type='application/json',
                                       title='Path to STAC metadata of source dataset.'))
    item.add_link(link=pystac.Link(rel='about',
                                   target=meta['prod']['doi'],
                                   title='Product Definition Reference.'))
    item.add_link(link=pystac.Link(rel='access',
                                   target=meta['prod']['access'],
                                   title='Product Definition Reference.'))
    item.add_link(link=pystac.Link(rel='related',
                                   target=meta['prod']['ancillaryData1'],
                                   title='Reference to ancillary data used in the generation process.'))
    # if meta['prod']['noiseRemovalApplied']:
    #     item.add_link(link=pystac.Link(rel='noise-removal',
    #                                    target=meta['prod']['noiseRemovalAlgorithm'],
    #                                    title='Reference to the noise removal algorithm details.'))
    item.add_link(link=pystac.Link(rel='radiometric-terrain-correction',
                                   target=meta['prod']['RTCAlgorithm'],
                                   title='Reference to the Radiometric Terrain Correction algorithm details.'))
    item.add_link(link=pystac.Link(rel='rtc-dem',
                                   target=meta['prod']['demReference'],
                                   title='The Digital Elevation Model used during Radiometric Terrain Correction'))                                   
    item.add_link(link=pystac.Link(rel='radiometric-accuracy',
                                   target=meta['prod']['radiometricAccuracyReference'],
                                   title='Reference describing the radiometric uncertainty of the product.'))
    item.add_link(link=pystac.Link(rel='geometric-correction',
                                   target=meta['prod']['geoCorrAlgorithm'],
                                   title='Reference to the Geometric Correction algorithm details.'))
    item.add_link(link=pystac.Link(rel='{}-model'.format(meta['prod']['demType']),
                                   target=meta['prod']['demReference'],
                                   title=meta['prod']['demName']))
    item.add_link(link=pystac.Link(rel='earth-gravitational-model',
                                   target=meta['prod']['demEgmReference'],
                                   title='Reference to the Earth Gravitational Model (EGM) used for Geometric Correction.'))
    item.add_link(link=pystac.Link(rel='geometric-accuracy',
                                   target=meta['prod']['geoCorrAccuracyReference'],
                                   title='Reference documenting the estimate of absolute localization error.'))
    item.add_link(link=pystac.Link(rel='gridding-convention',
                                   target=meta['prod']['griddingConventionURL'],
                                   title='Reference that describes the gridding convention used.'))
    
    if tifs:
        for tif in tifs:
            relpath = './' + os.path.relpath(tif, target).replace('\\', '/')
            
            if 'measurement' in tif:
                pol = re.search('[vh]{2}', tif).group().lower()
                created = datetime.fromtimestamp(os.path.getctime(tif)).isoformat()
                extra_fields = {'created': created,
                                'measurement_type': meta['prod']['backscatterMeasurement'],
                                'backscatter_convention': meta['prod']['backscatterConvention'],
                                'raster:bands': [{'unit':'natural',
                                                'nodata': 'NaN',
                                                'data_type': '{}{}'.format(meta['prod']['fileDataType'],
                                                                            meta['prod']['fileBitsPerSample']),
                                                'bits_per_sample': int(meta['prod']['fileBitsPerSample'])}],
                                'file:byte_order': meta['prod']['fileByteOrder'],
                                'file:header_size': os.path.getsize(tif),
                                'card4l:border_pixels': meta['prod']['numBorderPixels']}
                
                item.add_asset(key=pol,
                            asset=pystac.Asset(href=relpath,
                                                title='{} backscatter data'.format(pol.upper()),
                                                media_type=pystac.MediaType[meta['prod']['fileFormat']],
                                                roles=['backscatter', 'data'],
                                                extra_fields=extra_fields))
            
            elif 'annotation' in tif:
                key = re.search('-[a-z]{2}(?:-[a-z]{2}|).tif', tif).group()
                
                if key in ['-dm.tif', '-id.tif']:
                    ras_bands_base = {"unit": "mask",
                                    'nodata': 255,
                                    'data_type': 'uint8',
                                    'bits_per_sample': 8}
                    raster_bands = []
                    if key == '-dm.tif':
                        with Raster(tif) as dm_ras:
                            bands = dm_ras.bands
                        if bands > 1:  # multi-band data mask (default)
                            samples = list(SAMPLE_MAP[key]['values'].values())
                            samples.remove('layover and shadow')
                            if bands != len(samples):
                                raise RuntimeError('Mismatch between number of bands ({nbands}) of the '
                                                'multi-band data mask file and the number of keys '
                                                'in SAMPLE_MAP ({nkeys}).'.format(nbands=bands, nkeys=len(samples)))
                            for i in range(bands):
                                vals = {'values': [{'value': 1, 'summary': samples[i]}]}
                                band_dict = deepcopy(ras_bands_base)
                                band_dict.update(vals)
                                raster_bands.append(band_dict)
                        else:  # single-band data mask
                            vals = {'values': [{'value': [v], 'summary': s} for v, s in SAMPLE_MAP[key]['values'].items()]}
                    else:  # key == '-id.tif'
                        src_list = list(meta['source'].keys())
                        src_target = [os.path.basename(meta['source'][src]['filename']).replace('.SAFE', '').replace('.zip', '')
                                    for src in src_list]
                        vals = {'values': [{'value': [i+1], 'summary': s} for i, s in enumerate(src_target)]}
                    
                    if len(raster_bands) == 0:
                        band_dict = deepcopy(ras_bands_base)
                        band_dict.update(vals)
                        raster_bands = [band_dict]
                    
                    extra_fields = {'raster:bands': raster_bands,
                                    'file:byte_order': meta['prod']['fileByteOrder'],
                                    'file:header_size': os.path.getsize(tif)}
                
                else:
                    raster_bands = {'unit': SAMPLE_MAP[key]['unit'],
                                    'nodata': 'NaN',
                                    'data_type': '{}{}'.format(meta['prod']['fileDataType'],
                                                            meta['prod']['fileBitsPerSample']),
                                    'bits_per_sample': int(meta['prod']['fileBitsPerSample'])}
                    
                    if raster_bands['unit'] is None:
                        raster_bands.pop('unit')
                    
                    extra_fields = {'raster:bands': [raster_bands],
                                    'file:byte_order': meta['prod']['fileByteOrder'],
                                    'file:header_size': os.path.getsize(tif)}
                    
                    if key == '-ei.tif':
                        extra_fields['card4l:ellipsoidal_height'] = meta['prod']['ellipsoidalHeight']
                
                if SAMPLE_MAP[key]['role'] == 'noise-power':
                    asset_key = SAMPLE_MAP[key]['title'].lower().replace(' ', '-')
                else:
                    asset_key = SAMPLE_MAP[key]['role']
                
                item.add_asset(key=asset_key,
                            asset=pystac.Asset(href=relpath,
                                                title=SAMPLE_MAP[key]['title'],
                                                media_type=pystac.MediaType[meta['prod']['fileFormat']],
                                                roles=[SAMPLE_MAP[key]['role'], 'metadata'],
                                                extra_fields=extra_fields))
    item.save_object(dest_href=outname)


def source_json(meta, target):
    """
    Function to generate source-level metadata for an NRB target product in STAC compliant JSON format.
    
    Parameters
    ----------
    meta: dict
        Metadata dictionary generated with metadata.extract.meta_dict
    target: str
        A path pointing to the root directory of a product scene.
    
    Returns
    -------
    None
    """
    metadir = os.path.join(target, 'source')
    os.makedirs(metadir, exist_ok=True)
    
    for uid in list(meta['source'].keys()):
        scene = os.path.basename(meta['source'][uid]['filename']).split('.')[0]
        outname = os.path.join(metadir, '{}.json'.format(scene))
        
        start = meta['source'][uid]['timeStart']
        stop = meta['source'][uid]['timeStop']
        date = start + (stop - start)/2
        
        item = pystac.Item(id=scene,
                           geometry=None,
                           bbox=None,
                           datetime=date,
                           properties={})
        
        item.common_metadata.start_datetime = start
        item.common_metadata.end_datetime = stop 
        item.common_metadata.created = meta['source'][uid]['processingDate']
        item.common_metadata.instruments = [meta['common']['instrumentShortName']]
        item.common_metadata.platform = meta['common']['platformFullname']
        
        SarExtension.add_to(item)
        SatExtension.add_to(item)
        ViewExtension.add_to(item)
        sar_ext = SarExtension.ext(item)
        sat_ext = SatExtension.ext(item)
        item.stac_extensions.append('https://stac-extensions.github.io/processing/v1.1.0/schema.json')
        item.stac_extensions.append('https://stac-extensions.github.io/card4l/v1.0.0/sar/source.json')
        
        sar_ext.apply(instrument_mode=meta['common']['operationalMode'],
                      frequency_band=FrequencyBand[meta['common']['radarBand'].upper()],
                      polarizations=[Polarization[pol] for pol in meta['common']['polarisationChannels']],
                      product_type=meta['source'][uid]['productType'],
                      center_frequency=float(meta['common']['radarCenterFreq']),
                      resolution_range=meta['source'][uid]['rangeResolution'],
                      resolution_azimuth=meta['source'][uid]['azimuthResolution'],
                      pixel_spacing_range=float(meta['source'][uid]['rangePixelSpacing']),
                      pixel_spacing_azimuth=float(meta['source'][uid]['azimuthPixelSpacing']),
                      looks_range=int(meta['source'][uid]['rangeNumberOfLooks']),
                      looks_azimuth=int(meta['source'][uid]['azimuthNumberOfLooks']),
                      observation_direction=ObservationDirection[meta['common']['antennaLookDirection']])
        
        sat_ext.apply(orbit_state=OrbitState[meta['common']['orbit'].upper()],
                      relative_orbit=meta['common']['orbitNumbers_rel'],
                      absolute_orbit=meta['common']['orbitNumbers_abs'])
        
        item.properties['processing:facility'] = meta['source'][uid]['processingCenter']
        item.properties['processing:software'] = {meta['source'][uid]['processorName']:
                                                  meta['source'][uid]['processorVersion']}
        item.properties['proj:shape'] = [meta['source'][uid]['lineLength'], meta['source'][uid]['lineTimeInterval']]
        item.properties['processing:level'] = meta['source'][uid]['processingLevel']
        
        item.properties['card4l:specification'] = meta['prod']['card4l-name']
        item.properties['card4l:specification_version'] = meta['prod']['card4l-version']
        item.properties['card4l:beam_id'] = meta['source'][uid]['swathIdentifier']
        item.properties['card4l:orbit_data_source'] = meta['source'][uid]['orbitDataSource']
        item.properties['card4l:orbit_mean_altitude'] = float(meta['common']['orbitMeanAltitude'])
        item.properties['card4l:source_geometry'] = meta['source'][uid]['dataGeometry']
        item.properties['card4l:incidence_angle_near_range'] = meta['source'][uid]['incidenceAngleMin']
        item.properties['card4l:incidence_angle_far_range'] = meta['source'][uid]['incidenceAngleMax']
        item.properties['card4l:performance_indicator_near_range'] = meta['source'][uid]['neszNear']
        item.properties['card4l:performance_indicator_far_range'] = meta['source'][uid]['neszFar']        
        item.properties['card4l:noise_equivalent_intensity'] = meta['source'][uid]['perfEstimates']
        item.properties['card4l:noise_equivalent_intensity_type'] = meta['source'][uid]['perfNoiseEquivalentIntensityType']
        item.properties['card4l:mean_faraday_rotation_angle'] = meta['source'][uid]['faradayMeanRotationAngle']
        item.properties['card4l:ionosphere_indicator'] = meta['source'][uid]['ionosphereIndicator']
        
        item.add_link(link=pystac.Link(rel='card4l-document',
                                       target=meta['prod']['card4l-link'].replace('.pdf', '.docx'),
                                       media_type='application/vnd.openxmlformats-officedocument.wordprocessingml'
                                                  '.document',
                                       title='CARD4L Product Family Specification v{}: Normalised Radar Backscatter'
                                             ''.format(meta['prod']['card4l-version'])))
        item.add_link(link=pystac.Link(rel='card4l-document',
                                       target=meta['prod']['card4l-link'],
                                       media_type='application/pdf',
                                       title='CARD4L Product Family Specification v{}: Normalised Radar Backscatter'
                                             ''.format(meta['prod']['card4l-version'])))
        item.add_link(link=pystac.Link(rel='about',
                                       target=meta['source'][uid]['doi'],
                                       title='Product Definition Reference.'))
        item.add_link(link=pystac.Link(rel='access',
                                       target=meta['source'][uid]['access'],
                                       title='URL to data access information.'))
        item.add_link(link=pystac.Link(rel='satellite',
                                       target=meta['common']['platformReference'],
                                       title='CEOS Missions, Instruments and Measurements Database record'))
        item.add_link(link=pystac.Link(rel='state-vectors',
                                       target=meta['source'][uid]['orbitStateVector'],
                                       title='Orbit data file containing state vectors.'))
        item.add_link(link=pystac.Link(rel='sensor-calibration',
                                       target=meta['source'][uid]['sensorCalibration'],
                                       title='Reference describing sensor calibration parameters.'))
        item.add_link(link=pystac.Link(rel='pol-cal-matrices',
                                       target=meta['source'][uid]['polCalMatrices'],
                                       title='URL to the complex-valued polarimetric distortion matrices.'))
        item.add_link(link=pystac.Link(rel='referenced-faraday-rotation',
                                       target=meta['source'][uid]['faradayRotationReference'],
                                       title='Reference describing the method used to derive the estimate for the mean'
                                             ' Faraday rotation angle.'))
    
        item.save_object(dest_href=outname)


def main(meta, target, tifs):
    """
    Wrapper for `source_json` and `product_json`.
    
    Parameters
    ----------
    meta: dict
        Metadata dictionary generated with `metadata.extract.meta_dict`
    target: str
        A path pointing to the root directory of a product scene.
    tifs: list[str]
        List of paths to all GeoTIFF files of the currently processed NRB product.
    
    Returns
    -------
    None
    """
    
    source_json(meta=meta, target=target)
    product_json(meta=meta, target=target, tifs=tifs)
