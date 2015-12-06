"""
This is an implementation of Conway's Game of Life using opengl and pysdl2.
All of the code, including the shaders, will be contained in this file.
There will be no class structure in this code, just methods.
"""

import sys
import sdl2
import sdl2.ext
from sdl2 import video
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from PIL import Image

if __name__ == "__main__":
	width = 800
	height = 600
	title = "Game of Life"
	fps = 60
	screen = sdl2.SDL_CreateWindow(title, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, sdl2.SDL_WINDOW_OPENGL)
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 1)
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK, video.SDL_GL_CONTEXT_PROFILE_CORE)
	context = sdl2.SDL_GL_CreateContext(screen)
	startTime = sdl2.timer.SDL_GetTicks()
	currTime = startTime
	
	while True:
		events = sdl2.ext.get_events()
		for event in events:
			if event.type == sdl2.SDL_QUIT:
				sdl2.ext.quit()
				sys.exit()
				
		prevTime = currTime
		currTime = sdl2.timer.SDL_GetTicks()
		diff = currTime - prevTime
		frameRate = min(fps, 1000/diff) if diff != 0 else fps
		
		sdl2.SDL_GL_SwapWindow(screen)
		sdl2.SDL_Delay(1000/fps)
		print frameRate
		

