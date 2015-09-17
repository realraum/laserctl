/*
 *  laserctl
 *
 *
 *  Copyright (C) 2015 Christian Pointner <equinox@spreadspace.org>
 *
 *  This file is part of laserctl.
 *
 *  laserctl is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  laserctl is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with laserctl. If not, see <http://www.gnu.org/licenses/>.
 */

#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/power.h>
#include <stdio.h>

#include "util.h"
#include "led.h"
#include "usbio.h"

#include "Arduino.h"
#include "FastLED.h"


#define NUM_LEDS 8
#define DATA_PIN 3    // PD0 @ Atmega32U4

// Define the array of leds
CRGB leds[NUM_LEDS];

void fastled_init()
{
  arduino_init();
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
}

void leds_set(CRGB color)
{
  uint8_t i;
  for(i = 0; i < NUM_LEDS; ++i) {
    leds[i] = color;
  }
  FastLED.show();
}

void handle_cmd(uint8_t cmd)
{
  switch(cmd) {
  case '0': leds_set(CRGB::Black); led_off(); break;
  case '1': leds_set(CRGB::White); led_on(); break;
  case 'r': leds_set(CRGB::Red); led_on(); break;
  case 'g': leds_set(CRGB::Green); led_on(); break;
  case 'b': leds_set(CRGB::Blue); led_on(); break;
  case '!': reset2bootloader(); break;
  default: printf("error\r\n"); return;
  }
  printf("ok\r\n");
}

int main(void)
{
  MCUSR &= ~(1 << WDRF);
  wdt_disable();

  cpu_init();
  led_init();
  usbio_init();
  fastled_init();
  sei();

  for(;;) {
    int16_t BytesReceived = usbio_bytes_received();
    while(BytesReceived > 0) {
      int ReceivedByte = fgetc(stdin);
      if(ReceivedByte != EOF) {
        handle_cmd(ReceivedByte);
      }
      BytesReceived--;
    }

    usbio_task();
  }
}
