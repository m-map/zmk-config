# Custom C compiled into the ZMK application for this config repo.
#
# nrf_butterfly_30 only: an onboard-LED layer indicator (see src/layer_led.c).
# Guarded on the shield so it is never compiled into the xiao_split_60 builds.
if(CONFIG_SHIELD_NRF_BUTTERFLY_30)
  zephyr_library()
  zephyr_library_sources(src/layer_led.c)
endif()
