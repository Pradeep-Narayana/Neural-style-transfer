**Neural style transfer**

This project consists of a neural network model to learn the artistic style from one image and transfer it to another.
This model can also be used to transfer styles between videos by breaking down the videos into frames.
Technologies used: Python, TensorFlow, Keras, Numpy, Matplotlib, Pillow.


There are two files in this project :
gatysstyletransfer.py and
gatysstyletransfer_animated.py

Directories - 
Images - keep style and content images for gatys style transfer
Output_Images - output after style transfer gets saved here in the format styleName_contentName.jpeg


gatysstyletransfer.py:

This file is used to apply style transfer for two images. One is the "style image" from which the style will be taken and another is the "content image" on which the style will be applied to.
There are two folders - Images and Output_Images.

Place the two images that you want to test within the folder "Images".
Once the program runs, the output generated will be automatically placed in the folder "Output_Images".
To run the program from terminal, use the command

python gatysstyletransfer.py <styleImageName.jpg> <contentImageName.jpg>


gatysstyletransfer_animated.py:

This file is used to apply style transfer to two GIFS. It takes the style from the first GIF and applies it to the content of the second GIF. It splits the GIFs into frames, applies the style transfer and then combines the frames again to create a GIF with the new style.

NOTE- the program will pause execution once an image is displayed you must close the image to continue execution

Directories - 
style - stores frames after splitting the style.gif file
content- stores frames after splitting the content.gif file
Transfer frames - stores the frames and the final gif after completion of program

Place the two gifs that you want to test with in the root folder.
Once the program runs, the output generated will be automatically placed in the folder "transfer frames".
To run the program from terminal, use the command

python gatysstyletransfer_animated.py <style.gif> <content.gif>

