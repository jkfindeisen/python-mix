# Python mix

A mix of Python scripts I might use in my daily work. [License](LICENSE) of presented scripts. No warranty - use at your
own risk.

## OBF Python support

The OBF (and MSR) file format is used within my department quite frequencly. See folder [obf](obf) for a pure Python OBF
content reader.

## JPEG XR file reading

I needed to read [JXR](https://en.wikipedia.org/wiki/JPEG_XR) files (in Python).
[Matlab](https://www.mathworks.com/help/matlab/import_export/supported-file-formats.html) does not support the file format.
[Pillow](https://pillow.readthedocs.io/en/stable/#) also does not support it.

[ImageIO](https://imageio.readthedocs.io/en/stable/format_jpeg-xr-fi.html)
says that it supports JXR via the [FreeImage](https://freeimage.sourceforge.io/) library, however it cannot load my
example image and gives an exception "No known error." instead. The exception is known (see question on [StackOverflow](https://stackoverflow.com/questions/50002135/how-to-load-an-jpeg-xr-image-file-in-python),
which refers to an [imageio issue](https://github.com/imageio/imageio/issues/269) which has been closed as upstream, i.e. related to the FreeImage library).

ImageIO uses "FreeImage-3.15.1-win64.dll". The current version of FreeImage is 3.18.0. There is another FreeImage Python
wrapper [freeimage-py](https://github.com/zpincus/freeimage-py) but it's 3 years old and there aren't any releases.

FreeImage itself relies on libjxr, the official JXR support library from Microsoft. libjxr resided
on codeplex (which will shutdown soon), copies are available on Github [here](https://github.com/4creators/jxrlib) and
[here](https://github.com/glencoesoftware/jxrlib) (with a Java wrapper for BioFormats, so ImageJ/Fiji might be able to
read my JXR files via BioFormats).

However, my version of Fiji (1.53c) with BioFormats (6.6.1) could not import the JXR file (UnknownFormatException).

So I give up for the moment. One could still do:

- check that the JXR file I have is a valid one with some conversion tool (like the official JxrDecApp ([make JxrDecApp](https://github.com/curasystems/jxrlib/blob/master/Makefile)))
- debug ImageIO
- debug FreeImage
- debug jxrlib






