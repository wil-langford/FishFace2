FishFace2
=========

Find the location and orientation over time of a fish in a water flume.

The front end is a web interface using JavaScript and some JS libraries.  The middle is Django.
The back end is a combination of filesystems, databases, and Celery task modules.

In the current state, data collection is semi-automatic and fairly robust.  Users can manually tag
images with data to be consumed later by machine learning algorithms.  They can also verify the
accuracy of those manual tags.

There are two primary algorithms implemented currently for automatic tagging of data.

The preprocessing of the imagery has been automated in parallel.  At this stage, a naive, rough
orientation is available by algebraic manipulation of OpenCV-provided image moments.  The image
moments are further refined into Hu invariants, and those invariants are clustered using k-means.

The clusters are then used to estimate the required adjustment for each "shape" the fish can
assume when viewed from above.  This adjustment is applied to the raw orientation arrived at in
the earlier stage to obtain a cooked, more accurate orientation.
 
This algorithm is more general than the second, but it requires a relatively large number of manual
human tags to drive the clustering and subsequent stages.  It also doesn't deal as well with fish
in a flume due to water surface ripples causing segmentation issues.  The advantages of this
algorithm are its generality and relatively low CPU requirements when compared to the second.

The second algorithm can get by with relatively few human-supplied tags, but because it uses
ellipses for template matching, it's probably not suitable for locating animals that aren't
roughly elliptical with tails.  This algorithm also requires a relatively large amount of
computation time to tag imagery; a cluster is recommended.

There's a [rough and fairly old video demo](http://youtu.be/WdZm49Jv0d4) of the front end of an
early state of the application.


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
