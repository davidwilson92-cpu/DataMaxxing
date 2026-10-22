"""Validate the exported iPhone beta metadata before sending it to Apple."""
import plistlib
import sys
from pathlib import Path
from zipfile import ZipFile


def validate(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        info_names = [name for name in names if name.startswith('Payload/') and name.count('/') == 2 and name.endswith('.app/Info.plist')]
        if len(info_names) != 1:
            raise ValueError('Expected one iPhone application')
        info = plistlib.loads(archive.read(info_names[0]))
        expected = {
            'CFBundleIdentifier': 'com.zovasocial.app',
            'UIDeviceFamily': [1],
            'ZovaServerURL': 'https://zova-social.com',
            'ITSAppUsesNonExemptEncryption': False,
        }
        for key, value in expected.items():
            if info.get(key) != value:
                raise ValueError(f'Unexpected {key} in beta archive')
        if info.get('NSAppTransportSecurity', {}).get('NSAllowsArbitraryLoads'):
            raise ValueError('Arbitrary network loads are forbidden')
        for key in ('NSCameraUsageDescription', 'NSMicrophoneUsageDescription', 'NSPhotoLibraryUsageDescription'):
            if not isinstance(info.get(key), str) or not info[key].strip():
                raise ValueError(f'Missing {key}')
        manifest_path = info_names[0].replace('Info.plist', 'PrivacyInfo.xcprivacy')
        privacy = plistlib.loads(archive.read(manifest_path))
        if privacy.get('NSPrivacyTracking') is not False:
            raise ValueError('Unexpected tracking configuration')
    return 'iPhone identity, device family, privacy and HTTPS metadata verified'


if __name__ == '__main__':
    print(validate(Path(sys.argv[1])))
