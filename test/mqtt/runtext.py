#!/usr/bin/env python
# Display a runtext with double-buffering.
from samplebase import SampleBase
from rgbmatrix import graphics
import time


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")
	self.parser.add_argument("-co", "--color", help="The text color to display with name", default="blue")

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/10x20.bdf")

	if self.args.color == "red":
		textColor = graphics.Color(255,0,0)
	elif self.args.color == "green":
		textColor = graphics.Color(0,255,0)
	else:
		textColor = graphics.Color(0,0,255)

        #textColor = graphics.Color(255, 0, 0)
        pos = offscreen_canvas.width
        my_text = self.args.text

        while True:
        	offscreen_canvas.Clear()
	        len = graphics.DrawText(offscreen_canvas, font, pos, 20, textColor, my_text)
	        pos -= 1
	        if (pos + len < 0):
	            pos = offscreen_canvas.width
		    break

	        time.sleep(0.05)
	        offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
