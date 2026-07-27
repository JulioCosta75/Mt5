# Placeholder icon
This file is a placeholder. Replace `atlas.ico` with a real 256×256 multi-resolution
Windows .ico file before shipping. You can generate one from any 1024×1024 PNG using:
    https://www.icoconverter.com  (free)
    or:  ImageMagick:  convert atlas.png -define icon:auto-resize=256,128,96,64,48,32,16 atlas.ico

The build step (build.bat) and the .iss script both reference `icons\atlas.ico`.
NOTE: `SetupIconFile` (line 30 of atlas_setup.iss) is REQUIRED by the compiler.
If `atlas.ico` is missing, ISCC.exe FAILS the build with
"The system cannot find the file specified." (there is NO default fallback).
A real multi-resolution atlas.ico is now committed alongside atlas.png.
