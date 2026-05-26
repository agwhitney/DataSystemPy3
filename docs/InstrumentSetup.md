# Software Repositories
This repository is available on GitHub (https://github.com/agwhitney/DataSystemPy3) but it should be assumed that the instrument will not have internet access. To apply code repo changes to the instrument computer, set up a reference repository (called a bare repo) on the instrument which can be pushed to from the controlling computer.

GitHub <--push & pull--> Controlling Computer project --push--> Instrument bare repo <--pull-- Instrument project

## Initial Setup
### Step 1: Initialize Instrument Computer
This step should already be done.

On the instrument computer in the home directory `~`:
* Create two Git project folders: `git init DataSystemPy3` and `git init --bare DataSystemPy3.git`
* `cd DataSystemPy3` and `git remote add localbare ../DataSystemPy3.git`

The project folder now has DataSystemPy3.git as a reference with the label "localbare". Next, set up the controlling computer so that changes can be pushed to DataSystemPy3.git.

### Step 2: Initialize the Controlling Computer
This step should already be done on the HP Laptop, but you may also want to do it on other computers that might be used.

On the controlling computer in the existing project folder (presumably cloned from GitHub), simply add the remote reference: 
* `git remote add instrument ssh://msl@169.254.51.248/home/msl/DataSystemPy3.git`

To push changes to the instrument computer:
* `git push instrument main`
  * This updates the "main" branch on the instrument computer.