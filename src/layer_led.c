/*
 * Onboard-LED layer indicator for nrf_butterfly_30.
 *
 * Lights the XIAO's default (red) onboard LED while a chosen layer is active,
 * replicating the board's Arduino firmware, which turned its status LED on
 * whenever the toggled L2 layer was active.
 *
 * Compiled only for this shield (guarded in the top-level CMakeLists.txt on
 * CONFIG_SHIELD_NRF_BUTTERFLY_30), so it never affects the xiao_split_60 builds.
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/drivers/gpio.h>

#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>

/*
 * Layer to indicate. Matches the layer order in
 * boards/shields/nrf_butterfly_30/layout.txt: 0=base, 1=l2, 2=num, 3=sym.
 * Change this single value to point the LED at a different layer.
 */
#define LAYER_LED_WATCH 1

/* Board alias led0 = the red LED (P0.26, active-low) on the XIAO BLE. */
static const struct gpio_dt_spec layer_led = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

static int layer_led_listener(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    /* GPIO spec carries GPIO_ACTIVE_LOW, so logical 1 = LED on. */
    gpio_pin_set_dt(&layer_led, zmk_keymap_layer_active(LAYER_LED_WATCH) ? 1 : 0);
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(butterfly_layer_led, layer_led_listener);
ZMK_SUBSCRIPTION(butterfly_layer_led, zmk_layer_state_changed);

static int layer_led_init(void) {
    if (!gpio_is_ready_dt(&layer_led)) {
        return -ENODEV;
    }
    return gpio_pin_configure_dt(&layer_led, GPIO_OUTPUT_INACTIVE);
}

SYS_INIT(layer_led_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
