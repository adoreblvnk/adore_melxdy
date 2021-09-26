# adore_melxdy

<img src="images/melxdy.png" width=150>

adore_melxdy: a Python YT music bot. Feel free to clone this repo as needed.

prod by blvnk.

---

## Usage

Type `-help` for command help menu.

### Features

- Play
- Pause
- Skip
- Queue
- Loop (single)
- Download

## Installation

### Buildpacks

![heroku buildpack setting](images/heroku_buildpack_setting.png)

adore_melxdy is created to be hosted from Heroku. Necessary Heroku Buildpacks are listed below.

- [heroku-opus](https://github.com/xrisk/heroku-opus.git)
- [heroku-buildpack-ffmpeg-latest](https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git)
- [heroku-buildpack-ffmpeg](https://github.com/alevosia/heroku-buildpack-ffmpeg.git) (optional)

### Credentials

![heroku env](images/env_heroku.png)

- API_KEY: [Google API Discovery Key](https://code.google.com/apis/console)
- DISCORD_TOKEN: Upon creation of an application in [Discord Developer Portal](https://discord.com/developers/applications), navigate to `Bot` & copy the token.
- SPOTIPY_CLIENT_ID & SPOTIPY_CLIENT_SECRET can be ignored.

### Kaffeine (Optional)

[Kaffeine](https://kaffeine.herokuapp.com/) prevents the Heroku free app from sleeping every 30 mins. Note that Heroku requires all free applications to sleep for 6 hours every day.

## Changelog

### v1 initial commit

- Includes everything stated in the above.
- Partial Spotify implementation.

## Credits

- prod by blvnk.
- [Shiro Itsuka](https://twitter.com/Shiro_Itsuka)