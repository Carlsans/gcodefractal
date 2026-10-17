from src.rust.gcode_bounds import get_bounds
b = get_bounds("/home/carl/PycharmProjects/gcodefractal/src/matrixtogcode/images/eclat.gcode")
print("Min X ",b.min_x," Max X ", b.max_x," Min Y ",b.min_y," Max Y ", b.max_y)  # b.found_x/found_y flag if an axis was absent
