FishFace2
=========

Find the location and orientation over time of a fish in a water flume.

The front end is a web interface, the middle is Django, and the back end is a combination of
filesystems, databases, and a custom written Python script to run the hardware from a Raspberry Pi.
In the current state, data collection is semi-automatic and fairly robust.  Users can manually tag
images with data to be consumed later by machine learning algorithms.  They can also verify the
accuracy of the manual tags.

Future plans include automatic tagging of images using a combination of computer vision, machine
learning, and parallel processing.

There's a [rough video demo](http://youtu.be/WdZm49Jv0d4) of an early state of the app.


Thanks
------

* Professor Zelick at Portland State University for providing the equipment and space for the  
  research that prompted this software.
* Nicholas Merrell for providing an interesting problem that needed solving.
* Jeff Wyckoff for providing a stable development environment via devops arcana.
* Vinh, Elspeth, Khadiya, and Robin for volunteering to manually tag thousands of images so that  
  my machine learning algorithms had something to chew on.

* The giants of open-source software upon whose shoulders I stand.
* For helping me to better use the wheels of those giants instead of reinventing shoddy and naive  
  replacement wheels of my own, _Python Cookbook_, 3rd Edition, O'Reilly. (c)2013 Beazley and  
  Jones. 978-1-449-34037-7
* JetBrains for providing an open-source project license of PyCharm.
