# How to Run:

set up the python venv with requirments.txt

run sim with:
python -m src

run gui with:
python -m src.gui.main_gui

modify src/__main__.py for the first time to create the database
 - set function main to true, run once then set it back to false

# Stuff That Needs to Be Done
## General:
- Add Test files for all the modules
- Fix the graphs file
- Is there a better way to do constants.py??
- Apply Input Validation for all files aswell, make sure all functions do something

## Engine:
- Need to go over Kinematics ESP and make sure all implementations are using valid classes
- Figure out math to integrate solar cell power to SOC
    ^ Implement Battery Module After Motor module is complete

## Database:
- Why are there multiple parse_route files? Rename things to make them make more sense
- init_route_table gotta be remade so its more modular

## Utils:
 - Create a config type python module which takes some json files with a bunch of sim configs