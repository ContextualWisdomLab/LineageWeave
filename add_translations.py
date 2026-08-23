import re

with open("frontend/src/i18n.ts", "r") as f:
    content = f.read()

translations = {
    "Admin": {
        "ko": "관리자",
        "zh": "管理员",
        "ja": "管理者",
        "vi": "Quản trị viên"
    },
    "Admin settings": {
        "ko": "관리자 설정",
        "zh": "管理员设置",
        "ja": "管理者設定",
        "vi": "Cài đặt quản trị viên"
    },
    "Tenant brand name": {
        "ko": "테넌트 브랜드명",
        "zh": "租户品牌名称",
        "ja": "テナントブランド名",
        "vi": "Tên thương hiệu khách thuê"
    },
    "Save settings": {
        "ko": "설정 저장",
        "zh": "保存设置",
        "ja": "設定を保存",
        "vi": "Lưu cài đặt"
    },
    "Settings saved!": {
        "ko": "설정이 저장되었습니다!",
        "zh": "设置已保存！",
        "ja": "設定が保存されました！",
        "vi": "Đã lưu cài đặt!"
    }
}

for eng, trans in translations.items():
    content = content.replace(f'    Refresh: "새로 고침",', f'    Refresh: "새로 고침",\n    "{eng}": "{trans["ko"]}",')
    content = content.replace(f'    Refresh: "조회",', f'    Refresh: "조회",\n    "{eng}": "{trans["ko"]}",')

    content = content.replace(f'    Refresh: "刷新",', f'    Refresh: "刷新",\n    "{eng}": "{trans["zh"]}",')
    content = content.replace(f'    Refresh: "更新",', f'    Refresh: "更新",\n    "{eng}": "{trans["ja"]}",')
    content = content.replace(f'    Refresh: "Làm mới",', f'    Refresh: "Làm mới",\n    "{eng}": "{trans["vi"]}",')

with open("frontend/src/i18n.ts", "w") as f:
    f.write(content)
