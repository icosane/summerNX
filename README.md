# summerNX
English translation patches for Nintendo Switch homebrew ports of `Amanatsu ~Perfect Edition~` and `Amanatsu+`.

<br>For `Amanatsu ~Perfect Edition~` check for following title id: `0100CA584B72C000`
<br>For `Amanatsu+` check for following title id: `05000A072A2A8000`


# Installation for `Amanatsu ~Perfect Edition~`
1. Download `EN patch.7z` from Releases, unpack it
2. Create folders `0100CA584B72C000` in `atmosphere/contents/` and `romfs` in `atmosphere/contents/0100CA584B72C000`.
3. Copy either current `root.pfs.050` or the one in `./old` to `atmosphere/contents/0100CA584B72C000`
4. Play game


There is a minor issue with the Settings background, due to layout differences between the EN PC version and the JP PC version (homebrew base).

#
I'm not exactly sure about LFS patching, so the old file included only translations, omitting other files in the original `root.pfs.050`. Current patch should now be consistent with the original file.

-----------
# Installation for `Amanatsu+`
1. Download `plus_patch.7z` from Releases, unpack it
2. Copy extracted folder `05000A072A2A8000` to `atmosphere/contents/`.
3. Play game

From the port author (translated from Chinese): 
>The game text has been replaced with PingFang and enlarged to avoid eye strain.
><br>There are some issues with the game's shader settings. When the character's face is close to the background and zoomed in, the background only shows black due to the shader issue. The engine on the NS uses OpenGL. The game defaults to Direct3D, but OpenGL can be used in the main game. I've been working on the epilogue for a long time but haven't gotten it working properly yet. This is the best I can do for now; I'll work on finding the problems later.

# Thanks to
- [pfs-rs](https://github.com/sakarie9/pfs-rs)
- [zxc944464161](https://www.tekqart.com/thread-372733-1-1.html)
- [chatgpt4o汉化补丁](https://www.tekqart.com/thread-395846-1-1.html)
