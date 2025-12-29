# GUI INSTRUCTIONS

- To run, type `py -m src.gui.main_gui` in the terminal.
- Upload a kml file using the "Browse" button at the top. To use ASC2024 track, press cancel in the browse menu.
- Select a placemark from the dropdown. Then, either generate the map using generate from placemark (no simulation) or generate from time nodes (with simulation). The time step can be modified with the numerical input on the right side of the top bar.
- If the map was generated with simulation, graphs can be generated using the simulation data. Choose the desired x and y values for each graph and press the generate_graphs button.

## Debugging

- If an error occurs, there is a status bar at the bottom that will print any errors or any success messages.
- Map generation can take a long time if the time step is small. If the map hasn't generated for 5-10 minutes, then there may be an error.
