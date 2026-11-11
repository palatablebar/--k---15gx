"""PII 识别规则表（正则 / 号段 / 姓氏 / 地址关键词 / GB11643 权重）。

规则本身是纯数据 + 纯函数，落在 utils 便于 service 与 seed 共用，
不依赖数据库、不依赖请求上下文。
"""
from __future__ import annotations

import re

# ---- 手机号：11 位 + 号段白名单（工信部常用号段）----
MOBILE_RE = re.compile(r"^1[3-9]\d{9}$")
MOBILE_SEGMENTS = {
    "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
    "145", "147", "149", "150", "151", "152", "153", "155", "156", "157",
    "158", "159", "162", "165", "166", "167", "170", "171", "172", "173",
    "175", "176", "177", "178", "180", "181", "182", "183", "184", "185",
    "186", "187", "188", "189", "191", "193", "195", "196", "198", "199",
}

# ---- 身份证：18 位 + GB 11643-1999 加权校验位 ----
ID_CARD_RE = re.compile(r"^\d{17}[\dXx]$")
ID_CARD_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
ID_CARD_CHECK_CODES = "10X98765432"
# 行政区划前 2 位（省级）白名单，用于排除明显的随机数字串
ID_CARD_PROVINCE_PREFIXES = {
    "11", "12", "13", "14", "15", "21", "22", "23", "31", "32", "33", "34",
    "35", "36", "37", "41", "42", "43", "44", "45", "46", "50", "51", "52",
    "53", "54", "61", "62", "63", "64", "65", "71", "81", "82", "91",
}

# ---- 邮箱 ----
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# ---- 中文姓名：姓氏表 + 2~4 个汉字 ----
COMMON_SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙"
    "叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双"
    "闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮牛寿通边扈燕冀郏浦尚农"
    "温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空"
    "曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)
CJK_RE = re.compile(r"^[\u4e00-\u9fa5]{2,4}$")

# 复姓（4 字姓名必须命中复姓，避免"高脂血症"这类医学名词误报）
COMPOUND_SURNAMES = {
    "欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙", "慕容",
    "司徒", "令狐", "宇文", "长孙", "夏侯", "端木", "西门", "南宫", "独孤",
    "轩辕", "闻人", "澹台", "公冶", "宗政", "濮阳", "淳于", "太叔", "申屠",
    "公羊", "乐正", "拓跋", "百里", "东郭", "呼延", "梁丘", "左丘", "东门",
}

# 常见名字用字：2~3 字姓名要求名部字符属于此集合，
# 否则"全科""高科"这类科室名会被当成姓名（实测 department 列误报 333 条）。
COMMON_GIVEN_CHARS = set(
    "建国秀兰志强海燕文博雅静宁远若溪明哲嘉禾清和亦望舒牧之南乔书言知姝砚白诚云"
    "芳伟娜敏丽军磊洋勇艳杰娟涛超霞平刚桂英华玉萍红娥玲芬彬鹏辉斌宇浩凯健俊帆帅旭"
    "阳晨雨欣悦怡然子轩睿泽思彤佳琪梦洁雪梅松柏峰岚海洋天明月星辰光耀祖德福寿康"
    "安全民晓春秋冬夏东西南北中正大光明丽华美玲玉珍凤英秀英桂兰淑珍素芬慧敏静波"
    "立新春生树林森江河湖海山峰岩石金木水火土仁义礼智信忠孝廉耻勇勤俭谦和"
)

# ---- 地址：关键词 + 长度 ----
ADDRESS_KEYWORDS = (
    "省", "市", "区", "县", "镇", "乡", "街道", "路", "街", "巷", "号",
    "号楼", "栋", "单元", "室", "村", "小区", "大厦", "广场", "园区",
)
ADDRESS_MIN_LENGTH = 8


def mobile_ok(value: str) -> bool:
    return bool(MOBILE_RE.match(value)) and value[:3] in MOBILE_SEGMENTS


def id_card_checksum(value: str) -> bool:
    """GB 11643-1999：前 17 位加权求和 mod 11 → 校验码。"""
    if not ID_CARD_RE.match(value):
        return False
    if value[:2] not in ID_CARD_PROVINCE_PREFIXES:
        return False
    total = sum(int(value[i]) * ID_CARD_WEIGHTS[i] for i in range(17))
    return ID_CARD_CHECK_CODES[total % 11] == value[17].upper()


def name_ok(value: str) -> bool:
    """中文姓名：姓氏表 + 长度 + 名部用字校验。

    2 字：姓 + 常见名用字；3 字：姓 + 2 个名用字；4 字：必须复姓开头 + 2 个名用字。
    这样能挡掉「全科」「高脂血症」「原发性高血压」这类非姓名短语。
    """
    stripped = value.strip()
    if not CJK_RE.match(stripped):
        return False
    length = len(stripped)
    if length == 2:
        return stripped[0] in COMMON_SURNAMES and stripped[1] in COMMON_GIVEN_CHARS
    if length == 3:
        return stripped[0] in COMMON_SURNAMES and all(
            char in COMMON_GIVEN_CHARS or char in COMMON_SURNAMES for char in stripped[1:]
        )
    if length == 4:
        return stripped[:2] in COMPOUND_SURNAMES and all(
            char in COMMON_GIVEN_CHARS for char in stripped[2:]
        )
    return False


def address_ok(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < ADDRESS_MIN_LENGTH:
        return False
    return any(keyword in stripped for keyword in ADDRESS_KEYWORDS)


def email_ok(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


def is_placeholder(value: str) -> bool:
    """被上游预先掩码过的占位值（含 * 或 X 掩码），不参与命中率分母。"""
    return "*" in value or value.count("X") >= 6
