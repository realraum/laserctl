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


char line[64];
size_t line_offset = 0;

#define NUM_LEDS 8
#define NUM_FRAMES 32

typedef struct {
  CRGB leds[NUM_LEDS];
  uint8_t delay;
} frame_t;

typedef struct {
  frame_t frames[NUM_FRAMES];
  uint8_t len;
  uint8_t offset;
} animation_t;

animation_t animation[2];
uint8_t animation_idx = 0;
#define ACTIVE animation_idx
#define INACTIVE (animation_idx ? 0 : 1)

CRGB ledsout[NUM_LEDS];
#define DATA_PIN 23    // PD5 @ Teensy

void animation_init()
{
  arduino_init();
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(ledsout, NUM_LEDS);
}

void animation_task(void)
{
  // TODO:
  //  delay elapsed?  NO-> return
  //  YES:
  //  increment-with-wraparound(animation[ACTIVE].offset)
  //  ledsout = animation[ACTIVE].frames[animation[ACTIVE].offset].leds
  //  nextdelay = animation[ACTIVE].frames[animation[ACTIVE].offset].delay
}



bool read_line(void)
{
  usbio_task();
  int16_t BytesReceived = usbio_bytes_received();
  while(BytesReceived > 0) {
    int ReceivedByte = fgetc(stdin);
    BytesReceived--;
    if(ReceivedByte == EOF)
      line_offset = 0;
    else {
      line[line_offset] = (char)ReceivedByte;
      switch(line[line_offset]) {
      case '\r':
      case '\n': {
        line[line_offset] = 0;
        line_offset = 0;
        return true;
      }
      default: {
        line_offset++;
        if(line_offset >= sizeof(line)) line_offset = 0;
        break;
      }
      }
    }
  }
  return false;
}

void parse_line(void)
{
  led_on();
      // TODO:
      // if Line ~= 'Sll' -> reset animation[PASSIVE].offset, animation[PASSIVE].len = ll
      // if Line ~= 'Fddxxx....xxx -> animation[PASSIVE].frames[animation[ACTIVE].offset].delay = dd,
      //                              animation[PASSIVE].frames[animation[ACTIVE].offset].leds = xxx...xxxx
      // if Line ~= 'E' -> animation[PASSIVE].offset = 0, PASSIVE <-> ACTIVE
  led_off();
}



int main(void)
{
  MCUSR &= ~(1 << WDRF);
  wdt_disable();

  cpu_init();
  led_init();
  usbio_init();
  animation_init();
  sei();

  for(;;) {
    if(read_line()) {
      parse_line();
    }
    animation_task();
  }
}
