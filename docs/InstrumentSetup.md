Assume that HAMMR-HD will in general not have internet access.


# Software Repositories
This setup can also apply to the hyperspectral software.

This repository is available on GitHub, but the instrument will be unable to access GitHub. To apply changes to the instrument computer, set up a bare repo on the instrument which can be pushed to from the controlling laptop:

GitHub <--push & pull--> Laptop --push--> Instrument

To do this, on the instrument computer in the home directory `~`:
* Create two Git project folders: `git init project` and `git init --bare project.git`
  * Replace "project" with a sensible name.
* `cd project` and `git remote add label ../project.git`
  * Replace "label" with a sensible name.

The project folder now looks to the project.git folder for reference. We will set up the controlling laptop so that we can push changes to project.git.

On the controlling laptop in the existing project folder (presumably cloned from GitHub):
* `git remote add instrument ssh:msl@169.265.51.248/home/msl/project`
* `git push instrument master`
  * Run this whenever you want to update the master branch on the instrument.