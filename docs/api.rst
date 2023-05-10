API Documentation
=================


Configuration
-------------

.. automodule:: ERS_NRB.config
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        gdal_conf
        geocode_conf
        get_config

Tile Extraction
-------------

.. automodule:: ERS_NRB.tile_extraction
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        no_aoi
        tiles_from_aoi
        description2dict
        extract_tile

Processing
----------

.. automodule:: ERS_NRB.processor
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        main
        prepare_dem
        nrb_processing

Ancillary Functions
-------------------

.. automodule:: ERS_NRB.ancillary
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        generate_unique_id
        get_max_ext
        set_logging
        generate_unique_id
        create_rgb_vrt
        vrt_relpath
        vrt_pixfun

Metadata
--------

Extraction
^^^^^^^^^^

.. automodule:: ERS_NRB.metadata.extract
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        calc_performance_estimates
        get_prod_meta
        meta_dict
        vec_from_srccoords

STAC
^^^^

.. automodule:: ERS_NRB.metadata.stacparser
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        product_json
        source_json

XML
^^^^

.. automodule:: ERS_NRB.metadata.xmlparser
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        product_xml
        source_xml       