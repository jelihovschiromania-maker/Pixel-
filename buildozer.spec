[app]

title = Pixel Survival
package.name = pixelsurvival
package.domain = org.demo

source.dir = .
source.include_exts = py

version = 1.0
requirements = python3,kivy

orientation = landscape
fullscreen = 1

android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
