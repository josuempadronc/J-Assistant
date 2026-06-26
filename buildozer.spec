[app]

title           = J
package.name    = jassistant
package.domain  = com.cristmedicals
version         = 1.0

source.dir      = .
source.include_exts = py,kv,png,jpg,ttf,mp3,ogg,wav,flac

entrypoint      = main

requirements    = python3,kivy,pyjnius,android

orientation     = portrait
fullscreen      = 1

android.minapi          = 21
android.api             = 33
android.ndk             = 25c

android.sdk_path        = /usr/local/lib/android/sdk
android.ndk_path        = /usr/local/lib/android/sdk/ndk/25.2.9519653

android.permissions     = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,RECORD_AUDIO,READ_MEDIA_AUDIO,CALL_PHONE,READ_CONTACTS,WRITE_CONTACTS,SEND_SMS,READ_SMS,RECEIVE_SMS,CAMERA,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,READ_CALL_LOG,VIBRATE,MODIFY_AUDIO_SETTINGS,FLASHLIGHT,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,FOREGROUND_SERVICE,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
android.archs           = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

android.debug_artifact  = apk
android.release_artifact = aab

[buildozer]
log_level = 2
warn_on_root = 1
