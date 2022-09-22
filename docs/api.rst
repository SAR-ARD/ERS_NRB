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

AOI Generation
-------------

.. automodule:: ERS_NRB.tile_extraction
    :members:
    :undoc-members:
    :show-inheritance:

    .. autosummary::
        :nosignatures:

        no_aoi

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
        log
        set_logging

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

        calc_geolocation_accuracy
        calc_performance_estimates
        extract_pslr_islr
        geometry_from_vec
        get_header_size
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