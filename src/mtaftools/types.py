from typing import Union
from os import PathLike

# A type alias for file paths, allowing both string and PathLike objects.
PathType = Union[str, PathLike[str]] 
