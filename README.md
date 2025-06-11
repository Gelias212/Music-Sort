# Music Sort

Quick Sorting Script to organize large music libraries by fyle type, preserves folder structure (Eg:Artist/Album/Title.FLAC) artwork and .CUE files
Locks the processed folders to prevent re-processing the same files that have already been processed.

*It is recommended to use Foobar2000 and set the output to the original track folder and convert each track to an individual file*

## How to use:

  Install Python either via the .exe provided by their [website](https://www.python.org/downloads/) (Make sure to tick the "add python to PATH") or via the [Microsoft Store](https://apps.microsoft.com/detail/9ncvdn91xzqp?hl=en-US&gl=US)
  
  Place both Batch and Python scripts on the root of your music library, double click the batch file and choose the options according to your needs

https://github.com/user-attachments/assets/01a22004-e407-4cb1-83fc-74f0d1842935

## Folder Structuring

### Initial Structure
```
MusicLibrary/
├── Artist A/
│   ├── Album 1/
│   │   ├── track1.flac
│   │   ├── track2.m4a
│   │   ├── cover.jpg
│   │   └── info.txt
│   └── Album 2/
│       ├── song.mp3
│       └── booklet.pdf
├── Artist B/
│   └── Single/
│       ├── single.flac
│       └── art.png
└── Various Artists/
    ├── Compilation/
    │   ├── disc1/
    │   │   └── track.flac
    │   └── disc2/
    │       └── track.m4a
    └── Bonus/
        └── extra.mp3
```
### After Processing
```
MusicLibrary/
├── FLAC/  (Protected)
│   ├── Artist A/
│   │   ├── Album 1/
│   │   │   └── track1.flac
│   │   └── Album 2/  (Empty - removed)
│   └── Artist B/
│   │   └── Single/
│   │       └── single.flac
│   └── Various Artists/
│       ├── Compilation/
│       │   └── disc1/
│       │       └── track.flac
│       └── Bonus/  (Empty - removed)
├── AAC/  (Protected)
│   ├── Artist A/
│   │   ├── Album 1/
│   │   │   └── track2.m4a
│   │   └── Album 2/  (Empty - removed)
│   └── Various Artists/
│       └── Compilation/
│           └── disc2/
│               └── track.m4a
├── MP3/  (Protected)
│   ├── Artist A/
│   │   └── Album 2/
│   │       └── song.mp3
│   └── Various Artists/
│       └── Bonus/
│           └── extra.mp3
├── Artist A/  (Original - now empty)
├── Artist B/  (Original - now empty)
└── Various Artists/  (Original - now empty)
```
### Workflow
![Workflow](https://github.com/user-attachments/assets/def4a426-44a7-4a2a-87b0-a2d055f265d9)
