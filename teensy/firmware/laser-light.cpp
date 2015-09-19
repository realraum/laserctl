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
#define NUM_FRAMES 32

typedef struct {
  CRGB leds[NUM_LEDS];
  uint8_t delay;
} frame_t;

typedef struct {
  frame_t frames[NUM_FRAMES];
  uint8_t len;
  uint8_t current;
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

  ACTIVE = 0;
  memset(animation, 0, sizeof(animation));
}

void animation_task(void)
{
  // TODO:
  //  delay elapsed?  NO-> return
  //  YES:
  //  increment-with-wraparound(animation[ACTIVE].current)
  //  ledsout = animation[ACTIVE].frames[animation[ACTIVE].current].leds
  //  nextdelay = animation[ACTIVE].frames[animation[ACTIVE].current].delay
}

void animation_dump(uint8_t idx)
{
  uint8_t i;
  printf("animation[%s]: %d frames\r\n", idx == ACTIVE ? "active" : "inactive", animation[idx].len);
  for(i = 0; i < animation[idx].len; ++i) {
    printf("%3d: %c ", i, animation[idx].current < i ? '-' : (animation[idx].current == i ? '>' : '+'));
    uint8_t j;
    for(j = 0; j < NUM_LEDS; ++j) {
      printf("0x%02X%02X%02X ", animation[idx].frames[animation[idx].current].leds[j][0],
                                animation[idx].frames[animation[idx].current].leds[j][1],
                                animation[idx].frames[animation[idx].current].leds[j][2]);
    }
    printf(" %d ms\r\n", animation[idx].frames[animation[idx].current].delay);
  }
}



char line[64];
size_t line_pos = 0;

bool read_line(void)
{
  usbio_task();
  int16_t BytesReceived = usbio_bytes_received();
  while(BytesReceived > 0) {
    int ReceivedByte = fgetc(stdin);
    BytesReceived--;
    if(ReceivedByte == EOF)
      line_pos = 0;
    else {
      line[line_pos] = (char)ReceivedByte;
      switch(line[line_pos]) {
      case '\r':
      case '\n': {
        line[line_pos] = 0;
        return line_pos > 0 ? true : false;
      }
      default: {
        line_pos++;
        if(line_pos >= sizeof(line)) line_pos = 0;
        break;
      }
      }
    }
  }
  return false;
}

void parse_line(void)
{
  switch(line[0]) {
  case 'S': printf("Start: not yet implemented!\r\n"); break; // TODO: 'Sll'           -> reset animation[INACTIVE].current, animation[INACTIVE].len = ll
  case 'F': printf("Frame: not yet implemented!\r\n"); break; // TODO: 'Fddxxx....xxx' -> animation[INACTIVE].frames[animation[INACTIVE].current].delay = dd,
                   //                          animation[INACTIVE].frames[animation[INACTIVE].current].leds = xxx...xxxx
  case 'E': printf("End: not yet implemented!\r\n"); break; // TODO:  'E'            -> animation[INACTIVE].current = 0, ACTIVE = INACTIVE
  case 'D': animation_dump(ACTIVE); break;
  case 'd': animation_dump(INACTIVE); break;
  case '!': reset2bootloader(); break;
  }
  line_pos = 0;
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
