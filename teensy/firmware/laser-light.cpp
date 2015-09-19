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
      printf("0x%02X%02X%02X ", animation[idx].frames[i].leds[j][0],
                                animation[idx].frames[i].leds[j][1],
                                animation[idx].frames[i].leds[j][2]);
    }
    printf(" %3d ms\r\n", animation[idx].frames[i].delay);
  }
}



char line[64];
size_t line_pos = 0;

static inline uint8_t hextobin(uint8_t c)
{
  switch(c) {
  case '1': return 1;
  case '2': return 2;
  case '3': return 3;
  case '4': return 4;
  case '5': return 5;
  case '6': return 6;
  case '7': return 7;
  case '8': return 8;
  case '9': return 9;
  case 'a':
  case 'A': return 10;
  case 'b':
  case 'B': return 11;
  case 'c':
  case 'C': return 12;
  case 'd':
  case 'D': return 13;
  case 'e':
  case 'E': return 14;
  case 'f':
  case 'F': return 15;
  }
  return 0;
}

void handle_start(void)
{
  if(line_pos != 3) return;

  memset(&(animation[INACTIVE]), 0, sizeof(animation[INACTIVE]));
  animation[INACTIVE].len = hextobin(line[1]) << 4 | hextobin(line[2]);
  if(animation[INACTIVE].len > NUM_FRAMES)
    animation[INACTIVE].len = NUM_FRAMES;
}

void handle_frame(void)
{
// F1700112233445566778899AABBCCEEDDEEFF00112233445566
// F3fAA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55
  if((line_pos != (3 + NUM_LEDS*6)) || animation[INACTIVE].current >= NUM_FRAMES) return;

  animation[INACTIVE].frames[animation[INACTIVE].current].delay = hextobin(line[1]) << 4 | hextobin(line[2]);
  uint8_t i;
  for(i = 0; i < NUM_LEDS; ++i) {
    animation[INACTIVE].frames[animation[INACTIVE].current].leds[i][0] = hextobin(line[3 + i*6 + 0]) << 4 | hextobin(line[3 + i*6 + 1]);
    animation[INACTIVE].frames[animation[INACTIVE].current].leds[i][1] = hextobin(line[3 + i*6 + 2]) << 4 | hextobin(line[3 + i*6 + 3]);
    animation[INACTIVE].frames[animation[INACTIVE].current].leds[i][2] = hextobin(line[3 + i*6 + 4]) << 4 | hextobin(line[3 + i*6 + 5]);
  }
  animation[INACTIVE].current += animation[INACTIVE].current < NUM_FRAMES ? 1 : 0;
}

void handle_end(void)
{
  animation[INACTIVE].current = 0;
  ACTIVE = INACTIVE;
// TODO: restart animation_task
}

void parse_line(void)
{
  switch(line[0]) {
  case 'S': handle_start(); break;
  case 'F': handle_frame(); break;
  case 'E': handle_end(); break;
  case 'D': animation_dump(ACTIVE); break;
  case 'd': animation_dump(INACTIVE); break;
  case '!': reset2bootloader(); break;
  }
  line_pos = 0;
}

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
