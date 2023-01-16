# Tibetan-to-IAST

Tools to convert Indic from Tibetan Unicode to IAST.

## Example

```python
from tibskritconv import tibskrit_to_iast

tibskrit_to_iast('།ཀརྨྨོ་པ་དེ་ཤཾ་བྷིཀྵཱུ་ཎཱཾ་སརྦྦ་ཛྙཿཀརྟྟ་མུ་ཏྱ་ཏཿ།')
```

gives

```
|karmmo pa de śaṃ bhikṣū ṇāṃ sarbba jñaḥkartta mu tya taḥ|
```

The converter ignores characters it can't convert and adds a space at each tsheg.

## Using

The script is not present on Pypi yet, but since it fits into one file, you can integrate in an library easily.

## Resources

The file `tests/D4155.txt` is a transcription of the Sanskrit part of the Bodhisattvāvadānakalpalatā by Kṣemendra in volume 171 of the Derge Kangyur, made by [Esukhia](https://github.com/Esukhia/derge-tengyur/).

## Credits

The Python code is Copyright Elie Roux and Charles Li, 2023, and is available under the [MIT License](LICENSE.md).