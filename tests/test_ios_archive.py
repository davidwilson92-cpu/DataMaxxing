import plistlib
from zipfile import ZipFile

import pytest
from scripts.check_ios_archive import validate


def archive(tmp_path, **changes):
    info = {
        'CFBundleIdentifier': 'com.zovasocial.app', 'UIDeviceFamily': [1],
        'ZovaServerURL': 'https://zova-social.com', 'ITSAppUsesNonExemptEncryption': False,
        'NSCameraUsageDescription': 'Choose camera', 'NSMicrophoneUsageDescription': 'Choose video audio',
        'NSPhotoLibraryUsageDescription': 'Choose post media',
    }
    info.update(changes)
    path = tmp_path / 'synthetic.ipa'
    with ZipFile(path, 'w') as output:
        output.writestr('Payload/Zova.app/Info.plist', plistlib.dumps(info))
        output.writestr('Payload/Zova.app/PrivacyInfo.xcprivacy', plistlib.dumps({'NSPrivacyTracking': False}))
    return path


def test_rejects_the_unintended_ipad_family_that_apple_rejected(tmp_path):
    with pytest.raises(ValueError, match='UIDeviceFamily'):
        validate(archive(tmp_path, UIDeviceFamily=[1, 2]))
    assert 'verified' in validate(archive(tmp_path))


@pytest.mark.parametrize('changes', [
    {'CFBundleIdentifier': 'com.zovasocial.ios'},
    {'ZovaServerURL': 'https://untrusted.test'},
    {'NSAppTransportSecurity': {'NSAllowsArbitraryLoads': True}},
    {'NSPhotoLibraryUsageDescription': ''},
])
def test_rejects_wrong_app_server_or_privacy_metadata(tmp_path, changes):
    with pytest.raises(ValueError):
        validate(archive(tmp_path, **changes))
