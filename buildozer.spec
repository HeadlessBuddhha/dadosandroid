[app]
title = Welcome to Fear City
package.name = fearcitydice
package.domain = org.fearcity
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,ico
version = 2.0.0

requirements = python3,kivy==2.3.0,pillow

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/bg.png
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 0
