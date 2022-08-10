# AutoMediaManager (Amema)
Amema is a Python script used to organize media files such as movies and TV shows, naming them from scene-release-like naming to Plex/Kodi/etc. naming convention.
It scans the specified directories and matches the files with [TMDB API](https://www.themoviedb.org/documentation/api).

## How to use Amema
Make sure you have Python installed. Amema requires [Python](https://www.python.org/downloads/) 3.10 or greater.



 1. Download this repository by clicking `code`**->**`Download ZIP` in the top right corner
 2. Unpack the ZIP-file
 3. Rename or copy `config.sample.json` to `config.json`
 4. Edit `config.json` to suit your needs
 5. Open `bash`, `cmd` or any other `CLI`
 6. `CD` to the directory Amema is located at
 7. Run the command `python AutoMediaManager.py`
 8. Enjoy

## config.json
Here is a description for `config.json`:

This is the sample file:

    {
	    "directory": [
		    {
			    "input": "",
			    "output": "",
			    "media": "",
			    "action": ""
		    }
		],
		"tmdbConfirm": False,
		"tmdbKey": ""
	}

In `directory` you specify:
`input` as the directory you want to scan: `input: "/path/to/media"`
`output` as the directory where you want to put your files: `input: "/path/to/new/media"`
`media` as what type of media is going to be processed, can either be `movies` or `shows`
`action` as what action you want to take: `copy`, `cleancopy`, `move`, `cleanmove`, `symlink`

 - `copy` copies media files
 - `cleancopy` copies media files and removes other files and directories where media was found
 - `move` moves all files
 - `cleanmove` moves all media files and removes other files and directories where media was found
 - `symlink` creates symlink for media files

You can specify multiple `directory` by adding multiple blocks:
 

    "directory": [
		    {
			    "input": "path/to/media1",
			    "output": "path/to/new/media1",
			    "media": "movies",
			    "action": "cleanmove"
		    },
		    {
			    "input": "path/to/media2",
			    "output": "path/to/new/media1",
			    "media": "movies",
			    "action": "symlink"
		    },
		    {
			    "input": "path/to/media3",
			    "output": "path/to/media2",
			    "media": "shows",
			    "action": "copy"
		    }
			    
In `tmdbConfirm` you specify if the script should check file name with the [TMDB API](https://www.themoviedb.org/documentation/api), `tmdbConfirm` could be set to either `true` or `false`, if set to true, you hav to specify a [TMDB API](https://www.themoviedb.org/documentation/api) Key.

In `tmdbKey` you specify your key to the [TMDB API](https://www.themoviedb.org/documentation/api).