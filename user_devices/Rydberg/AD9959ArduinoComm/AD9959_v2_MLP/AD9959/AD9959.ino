/*
   Matthew Peters
*/

#include <SPI.h>
#include "AD9959.h"
#include "Channel.h"

/*
    Pin 10 is SS pin of Arduino Uno. Select pin 50 and 22 as IOUpdate and reset.
    Pin 7, 6, 5, 4 are for Profile 0 (p0), p1, p2, p3, respectively.
*/
AD9959 DDS(10, 50, 22, 7, 6, 5, 4);

//Channels on the DDS, the corresponding channel must be enabled to see an output on that channel
int CH[4]   = {0x10, 0x20, 0x40, 0x80};

// The length of the number of the command sent to the arduino over serial in bytes times 4 (each command has a channel flag,
// an integer telling you the number of values to set that follow (each value is 4 bytes), followed by the actual value bytes)
byte num_elements = 0;
int command = 0;
// This tells us which of the DDS channels we are changing
int flag = 0;
// a list of frequencies that we can store to send to the DDS. Up to 100 can be sent. If changing this number, you will also need to
// change it in the Channel class
long current_freq_list[100] = {0};
double phase = 0;



// input pins for stepping/resetting: the reset pin does not need to be used, but can be if you want.
int step_ch0_pin = 30;
int reset_ch0_pin = 31;
int step_ch1_pin = 32;
int reset_ch1_pin = 33;
int step_ch2_pin = 34;
int reset_ch2_pin = 35;
int step_ch3_pin = 40;
int reset_ch3_pin = 41;


// create channel classes for each channel output of the DDS

Channel ch0 = Channel(CH[0], step_ch0_pin, reset_ch0_pin);
Channel ch1 = Channel(CH[1], step_ch1_pin, reset_ch1_pin);
Channel ch2 = Channel(CH[2], step_ch2_pin, reset_ch2_pin);
Channel ch3 = Channel(CH[3], step_ch3_pin, reset_ch3_pin);
Channel channel_list[4] = {ch0, ch1, ch2, ch3};

void setup()
{
  // initialize our pins
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(step_ch0_pin, INPUT);
  pinMode(reset_ch0_pin, INPUT);
  pinMode(step_ch1_pin, INPUT);
  pinMode(reset_ch1_pin, INPUT);
  pinMode(step_ch2_pin, INPUT);
  pinMode(reset_ch2_pin, INPUT);
  pinMode(step_ch3_pin, INPUT);
  pinMode(reset_ch3_pin, INPUT);
  //  warming up of Serial port.
  Serial.begin(115200);
  while (!Serial) ;

  //  Start SPI
  //  In initialize(), set the External REF frequency in Hz.
  SPI.begin();
  DDS.initialize(20000000);
}

void loop() {

  if (Serial.available() >= 3) {
    // figure out which of the channels we will be setting
    flag = Serial.read();
    //Serial.println(flag);
    command = Serial.read();
    //Serial.println(command);
    // figure out how many commands need to be sent to DDS
    num_elements = Serial.read();
    //Serial.println(num_elements);

    // Here we set the frequency (command = 1)
    if (command == 1) {
      // for each 4-byte command string ...
      for (int a = 0; a < num_elements; a += 1) {
        while (Serial.available() < 4) {
          // delay until we have at least 4 bytes
          1 + 1;
        }
        // read the four bytes
        float temp1 = Serial.read();
        //Serial.print(temp1);
        float temp2 = Serial.read();
        //Serial.print(temp2);
        float temp3 = Serial.read();
        //Serial.println(temp1);
        float temp4 = Serial.read();
        // convert these bytes in a single long and put into our frequency list
        current_freq_list[a] = (temp1 * 16777216 + temp2 * 65536 + temp3 * 256 + temp4);

      }
      // send the frequency list to the Channel and set it
      channel_list[flag].setFreqList(num_elements, current_freq_list, DDS);
    }

    if (command == 2) {
      while (Serial.available() < 2) {
        // delay until we have at least 2 bytes
        1 + 1;
      }
      // read the two bytes
      float temp1 = Serial.read();
      float temp2 = Serial.read();
      phase = temp1 * 256 + temp2;
      channel_list[flag].setPhase(phase, DDS);
    }

  }

  for (int index = 0; index < 4; index ++) {
    // see if the step pin for our channel is high. If it is, increment to the next frequency in the list for this channel
    channel_list[index].checkStep(DDS);
    // see if the reset pin for our channel is high. If it is, reset the frequency to the first one in the list
    channel_list[index].checkReset(DDS);

    }
}
