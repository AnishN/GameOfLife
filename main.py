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
from OpenGL.GL import shaders
import numpy as np

"""
This handles setting the frame rate of the application.
Naively always waits 1/fps-th of a second for each tick.
Assumes no intensive work is done between frames.
"""
def tick():
	global currTime, screen, title, fpsDisplayCounter, fpsDisplayDelay
	prevTime = currTime
	currTime = sdl2.timer.SDL_GetTicks()
	diff = currTime - prevTime
	frameRate = min(fps, 1000/diff) if diff != 0 else fps
	sdl2.SDL_GL_SwapWindow(screen)
	sdl2.SDL_Delay(1000/fps)
	fpsDisplayCounter += diff
	if fpsDisplayCounter >= fpsDisplayDelay:
		sdl2.SDL_SetWindowTitle(screen, title + ": " + str(frameRate))
		fpsDisplayCounter = 0

"""
This sets the initial OpenGL rules for handling display.
Nothing too complex here as we only work in 2d.
"""
def initGL():
	glClearColor(0.0, 0.0, 0.0, 1.0)
	glClearDepth(1.0)
	glEnable(GL_TEXTURE_2D)

"""
This compiles the vertex and fragment shader strings into an OpenGL program.
Eventually for the Game of Life, 
"""
def initShaders():
	vsStr = """
	#version 120
	attribute vec2 position;
	void main()
	{
		gl_Position = vec4(position, 0, 1);
	}
	"""
	
	fs1Str = """
	#version 120
	uniform sampler2D state;
	uniform vec2 scale;

	int get(vec2 offset) {
		return int(texture2D(state, (gl_FragCoord.xy + offset) / scale).r);
	}

	void main() {
		int sum =
			get(vec2(-1.0, -1.0)) +
			get(vec2(-1.0,  0.0)) +
			get(vec2(-1.0,  1.0)) +
			get(vec2( 0.0, -1.0)) +
			get(vec2( 0.0,  1.0)) +
			get(vec2( 1.0, -1.0)) +
			get(vec2( 1.0,  0.0)) +
			get(vec2( 1.0,  1.0));
		if (sum == 3) {
			gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
		} else if (sum == 2) {
			float current = float(get(vec2(0.0, 0.0)));
			gl_FragColor = vec4(current, current, current, 1.0);
		} else {
			gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
		}
	}
	"""
	
	fs2Str = """
	uniform sampler2D state;
	uniform vec2 scale;
	uniform vec4 alive;
	uniform vec4 dead;
	
	void main()
	{
		vec4 color = texture2D(state, gl_FragCoord.xy / scale);
		if (color == vec4(1.0, 1.0, 1.0, 1.0))
		{
			gl_FragColor = alive;
		}
		else
		{
			gl_FragColor = dead;
		}
	}
	"""
	
	vs = shaders.compileShader(vsStr, GL_VERTEX_SHADER)
	fs1 = shaders.compileShader(fs1Str, GL_FRAGMENT_SHADER)
	fs2 = shaders.compileShader(fs2Str, GL_FRAGMENT_SHADER)
	
	program1 = shaders.compileProgram(vs, fs1)
	program2 = shaders.compileProgram(vs, fs2)
	out = (program1, program2)
	return out

"""
Wrapper for setting attributes for my Game of Life shader.
"""
def setShaderAttribute(program, aName, aType, aData):
	loc = glGetAttribLocation(program, aName)
	glEnableVertexAttribArray(loc)
	glBindBuffer(GL_ARRAY_BUFFER, aData)
	if aType == "vec2": 
		glVertexAttribPointer(loc, 2, GL_FLOAT, False, 0, None)

"""
Wrapper for setting uniforms for my simulation shader.
"""	
def setShaderUniform(program, uName, uType, uData):
	loc = glGetUniformLocation(program, uName)
	if uType == "sampler2D":
		glUniform1i(loc, uData)
	if uType == "vec2":
		glUniform2f(loc, *uData)
	if uType == "vec4":
		glUniform4f(loc, *uData)
	
"""
Wrapper for creating a texture in OpenGL.
Used for the front and back texture for the simuation.
Repeat makes the simulation wrap around.
Nearest disables interpolation of the cells.
Note that width and height are NOT window dimensions, but simulation dimensions.
"""
def createTexture(width, height):
	tex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, tex)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
	return tex

"""
Wrapper for creating the rectangle that covers the entire screen.
The simluation is rendered as a texture onto this quad.
"""
def createFullscreenQuad():
	quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1, 1, -1, -1, 1], dtype='float32')
	vbo = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glBufferData(GL_ARRAY_BUFFER, len(quad)*4, quad, GL_STATIC_DRAW)
	glBindBuffer(GL_ARRAY_BUFFER, 0)
	return vbo

"""
Draws the fullscreen quad that renders the simulation.
The division by eight is due to 4 bytes/float and 2 floats/vertex (2D).
"""
def drawFullscreenQuad():
	global vbo
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	vboSize = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE)
	numVertices = vboSize/8
	glBindBuffer(GL_ARRAY_BUFFER, 0)
	glDrawArrays(GL_TRIANGLES, 0, numVertices)

"""
Swaps the front and back textures in the simulation.
"""
def swapTextures():
	global front, back
	temp = front
	front = back
	back = temp

"""
Advances the simulation to the next generation (next step).
"""
def step():
	global fbo, back, front, program1, simWidth, simHeight
	glBindFramebuffer(GL_FRAMEBUFFER, fbo)
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, back, 0)
	glViewport(0, 0, simWidth, simHeight)
	glBindTexture(GL_TEXTURE_2D, front)
	glUseProgram(program1)
	setShaderAttribute(program1, "position", "vec2", vbo)
	setShaderUniform(program1, "state", "sampler2D", 0)
	setShaderUniform(program1, "scale", "vec2", (simWidth, simHeight))
	drawFullscreenQuad()
	swapTextures()
	glUseProgram(0)

"""
Renders the simulation to the screen for the user to see!
"""
def draw():
	global width, height, program2, alive, dead
	glBindFramebuffer(GL_FRAMEBUFFER, 0)
	glViewport(0, 0, width, height)
	glBindTexture(GL_TEXTURE_2D, front)
	glUseProgram(program2)
	setShaderAttribute(program2, "position", "vec2", vbo)
	setShaderUniform(program2, "state", "sampler2D", 0)
	setShaderUniform(program2, "scale", "vec2", (width, height))
	setShaderUniform(program2, "alive", "vec4", alive)
	setShaderUniform(program2, "dead", "vec4", dead)
	drawFullscreenQuad()
	glUseProgram(0)

"""
Initialized the front texture with a bunch of random values.
This sets up the starting state of the simulation.
Note that the alive and dead colors are the colors for the simulation.
Those colors are not ever displayed on the screen!
"""
def randomize():
	global front, simWidth, simHeight
	alive = (255, 255, 255, 255)
	dead = (0, 0, 0, 0)
	initialState = np.random.randint(2, size=simWidth*simHeight)
	initialColors = [alive if i == 1 else dead for i in initialState]
	initialColors = np.array(initialColors, dtype=np.uint8)
	glBindTexture(GL_TEXTURE_2D, front)
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, simWidth, simHeight, 0, GL_RGBA, GL_UNSIGNED_BYTE, initialColors)
	glBindTexture(GL_TEXTURE_2D, 0)

"""
Fills the screen with blackness before the randomization algorithm is complete.
Otherwise, the window was transparent upon initialization.
"""
def fillScreen():
	global screen, dead
	renderer = sdl2.SDL_CreateRenderer(screen, -1, 0)
	sdl2.SDL_SetRenderDrawColor(renderer, *[int(d * 255) for d in dead])
	sdl2.SDL_RenderClear(renderer)
	sdl2.SDL_RenderPresent(renderer)

if __name__ == "__main__":
	width = 800
	height = 600
	simWidth = 800
	simHeight = 600
	title = "Game of Life"
	fps = 60
	fpsDisplayCounter = 100
	fpsDisplayDelay = 100
	startTime = sdl2.timer.SDL_GetTicks()
	currTime = startTime
	alive = (222.0/255, 222.0/255, 222.0/255, 1.0)#alive color
	dead = (45.0/255, 45.0/255, 45.0/255, 1.0)#dead color
	
	screen = sdl2.SDL_CreateWindow(title, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, sdl2.SDL_WINDOW_OPENGL)
	fillScreen()
	
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 1)
	video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK, video.SDL_GL_CONTEXT_PROFILE_CORE)
	context = sdl2.SDL_GL_CreateContext(screen)
	initGL()
	program1, program2 = initShaders()
	
	vbo = createFullscreenQuad()
	front = createTexture(simWidth, simHeight)
	back = createTexture(simWidth, simHeight)
	fbo = glGenFramebuffers(1)
	
	randomize()
	
	while True:
		events = sdl2.ext.get_events()
		for event in events:
			if event.type == sdl2.SDL_QUIT:
				sdl2.ext.quit()
				sys.exit()
		
		glViewport(0, 0, width, height)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		step()
		draw()
		tick()
