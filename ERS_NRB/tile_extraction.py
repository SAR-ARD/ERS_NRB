from lxml import html
from spatialist.vector import Vector, wkt2vector
from shapely.geometry import box
from shapely.affinity import scale
from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from pyproj import Transformer

def tiles_from_aoi(vectorobject, kml, epsg=None):
    """
    Return a list of unique MGRS tile IDs that overlap with an area of interest (AOI) provided as a vector object.
    
    Parameters
    -------
    vectorobject: spatialist.vector.Vector
        The vector object to read.
    kml: str
        Path to the Sentinel-2 tiling grid kml file provided by ESA, which can be retrieved from:
        https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2/data-products
    epsg: int or list[int]
        define which EPSG code(s) are allowed for the tile selection.
    
    Returns
    -------
    tiles: list[str]
        A list of unique UTM tile IDs.
    """
    if isinstance(epsg, int):
        epsg = [epsg]
    with Vector(kml, driver='KML') as vec:
        tilenames = []
        vectorobject.layer.ResetReading()
        for item in vectorobject.layer:
            geom = item.GetGeometryRef()
            vec.layer.SetSpatialFilter(geom)
            for tile in vec.layer:
                tilename = tile.GetField('Name')
                if tilename not in tilenames:
                    attrib = description2dict(tile.GetField('Description'))
                    if epsg is not None and attrib['EPSG'] not in epsg:
                        continue
                    tilenames.append(tilename)
        vectorobject.layer.ResetReading()
        tile = None
        geom = None
        item = None
        return sorted(tilenames)


def extract_tile(kml, tile):
    """
    Extract a MGRS tile from the global Sentinel-2 tiling grid and return it as a vector object.
    
    Parameters
    ----------
    kml: str
        Path to the Sentinel-2 tiling grid kml file provided by ESA, which can be retrieved from:
        https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2/data-products
    tile: str
        The MGRS tile ID that should be extracted and returned as a vector object.
    
    Returns
    -------
    spatialist.vector.Vector
    """
    with Vector(kml, driver='KML') as vec:
        feat = vec.getFeatureByAttribute('Name', tile)
        attrib = description2dict(feat.GetField('Description'))
        feat = None
    return wkt2vector(attrib['UTM_WKT'], attrib['EPSG'])


def description2dict(description):
    """
    convert the HTML description field of the MGRS tile KML file to a dictionary.

    Parameters
    ----------
    description: str
        the plain text of the `Description` field

    Returns
    -------
    dict
        a dictionary with keys 'TILE_ID', 'EPSG', 'MGRS_REF', 'UTM_WKT' and 'LL_WKT'.
        The value of field 'EPSG' is of type integer, all others are strings.
    """
    attrib = html.fromstring(description)
    attrib = [x for x in attrib.xpath('//tr/td//text()') if x != ' ']
    attrib = dict(zip(attrib[0::2], attrib[1::2]))
    attrib['EPSG'] = int(attrib['EPSG'])
    return attrib


def main(config, spacing):
    """
    
    Parameters
    ----------
    config: dict
        Dictionary of the parsed config parameters for the current process.
    spacing: int
        The target pixel spacing in meters, which is passed to `pyroSAR.snap.util.geocode`.
    
    Returns
    -------
    geo_dict: dict
        Dictionary containing geospatial information for each unique MGRS tile ID that will be processed.
    align_dict: dict
        Dictionary containing 'xmax' and 'ymin' coordinates to use for the `standardGridOriginX` and
        `standardGridOriginY` parameters of `pyroSAR.snap.util.geocode`
    """
    
    if config['aoi_geometry'] is not None:
        with Vector(config['aoi_geometry']) as aoi:           
            tiles =  [x.name for x in aoi.getfeatures()]
            geo_dict = {}
            for tile in tiles:            
                ext = aoi.extent
                epsg = aoi.getProjection('epsg')
                xmax = ext['xmax'] - spacing / 2
                ymin = ext['ymin'] + spacing / 2
                geo_dict[tile] = {'ext': ext,
                                'epsg': epsg,
                                'xmax': xmax,
                                'ymin': ymin}
        
            align_dict = {'xmax': max([geo_dict[tile]['xmax'] for tile in list(geo_dict.keys())]),
                        'ymin': min([geo_dict[tile]['ymin'] for tile in list(geo_dict.keys())])}
            
            return geo_dict, align_dict            
    else:
        raise RuntimeError("'aoi_geometry' need to be provided!")
    



def no_aoi(ids, spacing):
    """
    
    Parameters
    ----------
    ids: list of pyroSAR.drivers.ID
        List containing the scenes to process.
    spacing: int
        The target pixel spacing in meters, which is passed to `pyroSAR.snap.util.geocode`.
    
    Returns
    -------
    geo_dict: dict
        Dictionary containing geospatial information for each scene that will be processed.
    align_dict: dict
        Dictionary containing 'xmax' and 'ymin' coordinates to use for the `standardGridOriginX` and
        `standardGridOriginY` parameters of `pyroSAR.snap.util.geocode`
    """
        
    geo_dict = {}
    for i, scene in enumerate(ids):
        #create transformer to convert points from lat lon to a UTM
        corners = scene.getCorners()
        utm_crs_list = query_utm_crs_info(
        datum_name = 'WGS 84',
        area_of_interest = AreaOfInterest(
            west_lon_degree = corners['xmin'],
            south_lat_degree= corners['ymin'],
            east_lon_degree = corners['xmin'],
            north_lat_degree = corners['ymin']))
        utm_crs = CRS.from_epsg(utm_crs_list[0].code)
        crs_lat_lon = CRS.from_epsg(4326)
        ## transform the LA tLON points to UTM
        transformer = Transformer.from_crs(crs_lat_lon, utm_crs,always_xy=True)
        ymin_utm, xmin_utm = transformer.transform(corners['xmin'],corners['ymin'])
        ymax_utm, xmax_utm = transformer.transform(corners['xmax'],corners['ymax'])


        ## create polygon using UTM points
        UTM_poly = box(ymin_utm, xmin_utm, ymax_utm, xmax_utm)
        UTM_poly_grown = scale(UTM_poly, xfact=1.2, yfact=1.2, zfact=0.0, origin='center') # grow the polygon by 20 % to ensure the AOI is covered 
        
        ext = {'xmin': UTM_poly_grown.bounds[0], 'xmax': UTM_poly_grown.bounds[2], 'ymin': UTM_poly_grown.bounds[1], 'ymax': UTM_poly_grown.bounds[3]}
        xmax = ext['xmax'] - spacing / 2
        ymin = ext['ymin'] + spacing / 2
        geo_dict[scene.outname_base()] = {'ext': ext,
                                'epsg': int(utm_crs_list[0].code),
                                'xmax': xmax,
                                'ymin': ymin}
        align_dict = {'xmax': max([geo_dict[tile]['xmax'] for tile in list(geo_dict.keys())]),
                        'ymin': min([geo_dict[tile]['ymin'] for tile in list(geo_dict.keys())])}
                      
    return geo_dict, align_dict