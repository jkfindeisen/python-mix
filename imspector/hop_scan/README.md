# Hop scanning in Imspector

Hop scanning (scanning along one axis in large jumps and then repeatedly shifting the offset) to fill the gaps with finely
pixelated data is interesting for some special microscopy modes.

Here, a Qt based GUI is made that interfaces with Imspector/SpecPy and starts a hop scan measurement and assembles the
data in the right order afterwards.

For a hop scan: choose a large step size along the first scan axis (x) and then introduce a "Custom Axis" (in scan mode
XY?) that shifts the offset of the x axis gradually.

The GUI uses icons from Material icons and from FlatIcon (see [license info](resources/license-info.txt)).
