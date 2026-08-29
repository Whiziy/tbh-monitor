"""
offsets.py — the TBH OFFSET BIBLE, all in one place (single source of truth).

Where it came from: IL2CPP dump (re/dump/dump.cs) of GameAssembly.dll v1.00.07, Unity
6000.0.72f1, TesseractStudio. EVERY value here is VALIDATED live (the meter ran with
them; gold/xp nailed to ±0.1%, stats match the .es3 save).
"""

from enum import IntEnum, IntFlag

PROCESS_NAME = "TaskBarHero.exe"
MODULE_NAME = "GameAssembly.dll"
POINTER_SIZE = 8
GOLD_KEY = 100001


class Obj:
    KLASS = 0x0


class String:
    LENGTH = 0x10
    CHARS = 0x14


class Array:
    MAX_LENGTH = 0x18
    DATA = 0x20


class List:
    ITEMS = 0x10
    SIZE = 0x18


class Dict:
    ENTRIES = 0x18
    COUNT = 0x20
    DATA = 0x20


class DictFloat:
    STRIDE = 0x10
    HASH = 0x0
    NEXT = 0x4
    KEY = 0x8
    VALUE = 0xC


class Dict8B:
    STRIDE = 0x18
    HASH = 0x0
    NEXT = 0x4
    KEY = 0x8
    VALUE = 0x10


class Class:
    NAME = 0x10
    ELEMENT_CLASS = 0x40
    CAST_CLASS = 0x48
    PARENT = 0x58
    STATIC_FIELDS = 0xB8


class Singleton:
    INSTANCE = 0x0


ACTK_FAKE = 0xC


class Unit:
    HEALTH_CONTROLLER = 0xB0
    IS_HERO = 0x100
    CACHE = 0x3B0
    CORE_STATS_OBSCURED = 0x104


class UnitHealthController:
    HP_CURRENT = 0x40
    HP_MAX = 0x4C


class Monster:
    STAGE_KEY = 0x3E8
    CACHE_OBSCURED = 0x3C0


class StageManager:
    HERO_LIST = 0x30


class MonsterSpawnManager:
    MONSTER_LIST = 0x28
    DEAD_MONSTER_LIST = 0x30
    SUMMONED_LIST = 0x38


class LogManager:
    LOG_LIST = 0x20
    LOG_BY_TYPE = 0x28


class StageClearLog:
    ACT = 0x40
    STAGE = 0x44
    CLEAR_TIME = 0x48
    IS_BOSS = 0x4C


class StageFailedLog:
    ACT = 0x40
    STAGE = 0x44
    NOW_WAVE = 0x48
    TOTAL_WAVE = 0x4C
    IS_ACT_BOSS = 0x50


class GetBoxLog:
    BOX_KEY = 0x40
    MONSTER_KEY = 0x48
    MONSTER_TYPE = 0x50


class HeroDieLog:
    KILLER_MONSTER = 0x40
    VICTIM_HERO = 0x48


class ResurrectionLog:
    HERO = 0x40


class CommonSaveData:
    PLAYTIME = 0x20
    CURRENT_STAGE_KEY = 0x58
    CURRENT_STAGE_WAVE = 0x5C


class PlayerSaveData:
    CURRENCIES = 0x68
    HEROES = 0x70
    ATTRIBUTES = 0x80
    RUNES = 0x90
    INVENTORY_SLOTS = 0x98
    STASH = 0xA0
    ITEMS = 0xC0
    AGGREGATES = 0xC8


class RuneSaveData:
    KEY = 0x10
    LEVEL = 0x14


class InventorySaveData:
    UNIQUE_ID = 0x18


class StashSaveData:
    UNIQUE_ID = 0x18


class AttributeSaveData:
    KEY = 0x10
    LEVEL = 0x14


class CurrencySaveData:
    KEY = 0x10
    QUANTITY = 0x18


class AggregateSaveData:
    TYPE = 0x10
    SUB_KEY = 0x14
    VALUE = 0x18


class HeroSaveData:
    HERO_KEY = 0x10
    LEVEL = 0x14
    EXP = 0x20
    EQUIPPED_ITEMS = 0x30
    EQUIPPED_SKILLS = 0x38


class ItemSaveData:
    ITEM_KEY = 0x10
    UNIQUE_ID = 0x18
    ENCHANT_DATA = 0x30


class ItemEnchant:
    STRIDE = 0x1C
    TIER = 0x4
    VALUE = 0x8
    RECIPE = 0xC
    STAT_TYPE = 0x18


class ItemInfoData:
    ITEM_KEY = 0x30
    ITEM_TYPE = 0x34
    GRADE = 0x38
    PARTS = 0x3C
    LEVEL = 0x6C


class HeroInfoData:
    HERO_KEY = 0x30
    CLASS_TYPE = 0x48


class StageInfoData:
    STAGE_KEY = 0x30
    STAGE_TYPE = 0x40
    DIFFICULTY = 0x44
    ACT = 0x48
    STAGE_NO = 0x4C
    WAVE_AMOUNT = 0x54
    WAVE_MOB_AMOUNT = 0x58


class HeroRuntime:
    INFO = 0x30
    STATS_HOLDER = 0x10
    LEVEL_HIDDEN = 0xD0
    LEVEL_KEY = 0xD4
    EXP_HIDDEN = 0x118
    EXP_KEY = 0x120
    LEVEL_FAKE = 0xD8
    EXP_FAKE = 0x128


class StatsHolder:
    MODIFIER_MGR = 0x10
    FINAL_STATS = 0x18
    SECOND = 0x20


class AggregateManager:
    AGGREGATES = 0x20


class StatModifier:
    STAT_TYPE = 0x10
    MOD_TYPE = 0x14
    VALUE = 0x18
    MOD_SOURCE = 0x1C


class DamageInfo:
    ATTACKER = 0x0
    ORIGIN_DAMAGE = 0x8
    IS_CRITICAL = 0xC
    DAMAGE_ATTRIBUTE = 0x10
    DAMAGE_TYPE = 0x14
    HIT_EFFECTS = 0x20


class StatType(IntEnum):
    NONE = 0; AttackDamage = 1; AttackSpeed = 2; CriticalChance = 3; CriticalDamage = 4
    MaxHp = 5; Armor = 6; MovementSpeed = 7; AreaOfEffect = 8; BaseAttackCountReduction = 9
    CooldownReduction = 10; SkillRangeExpansion = 11; FireResistance = 12; ColdResistance = 13
    LightningResistance = 14; ChaosResistance = 15; DodgeChance = 16; BlockChance = 17
    MaxDodgeChance = 18; MaxBlockChance = 19; Multistrike = 20; HpLeech = 21; ProjectileCount = 22
    HpRegenPerSec = 23; PhysicalDamagePercent = 24; FireDamagePercent = 25; ColdDamagePercent = 26
    LightningDamagePercent = 27; ChaosDamagePercent = 28; MaxFireResistance = 29
    MaxColdResistance = 30; MaxLightningResistance = 31; MaxChaosResistance = 32; AddHpPerHit = 33
    DamageReduction = 34; PhysicalDamageReduction = 35; FireDamageReduction = 36
    ColdDamageReduction = 37; LightningDamageReduction = 38; ChaosDamageReduction = 39
    DamageAbsorption = 40; DamageAddition = 41; PhysicalDamageAddition = 42; FireDamageAddition = 43
    ColdDamageAddition = 44; LightningDamageAddition = 45; ChaosDamageAddition = 46
    IncreaseExpAmount = 47; AdditionalExp = 48; CastSpeed = 49; SkillHealIncrease = 50
    SkillDurationIncrease = 51; AllElementalResistance = 52; IncreaseProjectileDamage = 53
    IncreaseMeleeDamage = 54; IncreaseAreaOfEffectDamage = 55; IncreaseSummonDamage = 56
    IncreaseProjectileSpeed = 57; AddHpPerKill = 58; AddAllSkillLevel = 59
    ElementalBlockChance = 60; ElementalDodgeChance = 61; MaxElementalBlockChance = 62
    MaxElementalDodgeChance = 63


class EAggregateType(IntEnum):
    MonsterKill = 0; HeroDeath = 1; GoldEarn = 2; BoxObtain = 3; ItemObtain = 4; Synthesis = 5
    Alchemy = 6; Crafting = 7; Offering = 8; Extraction = 9; Decoration = 10; Engraving = 11
    Inscription = 12; StageClear = 13; StageFail = 14; PlayTime = 15; BoxOpen = 16


class ELogType(IntEnum):
    NONE = 0; StageClear = 1; GetItemWithBoxOpen = 2; GetBox = 3; HeroDie = 4; HeroResurrection = 5
    HeroLevelUp = 6; StageFailed = 7; SynthesisResult = 8; AlchemyResult = 9; DecorationResult = 10
    EngravingResult = 11; InscriptionResult = 12; OfferingResult = 13; CraftingResult = 14
    ExtractionResult = 15


class EMonsterLogType(IntEnum):
    Monster = 0; Boss = 1; ActBoss = 2


class EDamageAttribute(IntEnum):
    Physical = 0; Fire = 1; Cold = 2; Lightning = 3; Chaos = 4; AllElement = 5; NONE = 6


class EDamageType(IntFlag):
    NONE = 0; Melee = 1; Projectile = 2; AOE = 4; Summon = 8; DOT = 16; Trap = 32


class EEquipClassType(IntEnum):
    All = 0; Knight = 1; Ranger = 2; Sorcerer = 3; Priest = 4; Hunter = 5; Slayer = 6


class EGradeType(IntEnum):
    COMMON = 0; UNCOMMON = 1; RARE = 2; LEGENDARY = 3; IMMORTAL = 4; ARCANA = 5; BEYOND = 6
    CELESTIAL = 7; DIVINE = 8; COSMIC = 9; NONE = 10


class EItemParts(IntEnum):
    NONE = 0; MAIN_WEAPON = 1; SUB_WEAPON = 2; HELMET = 3; ARMOR = 4; GLOVES = 5; BOOTS = 6
    AMULET = 7; EARING = 8; RING = 9; BRACER = 10


class ERecipeType(IntEnum):
    ALCHEMY = 0; SYNTHESIS = 1; CRAFTING = 2; DECORATION = 3; ENGRAVING = 4; INSCRIPTION = 5
    OFFERING = 6; EXTRACTION = 7; NONE = 8


class EStageDifficulty(IntEnum):
    Normal = 0; Nightmare = 1; Hell = 2; Torment = 3


class EStageType(IntEnum):
    NORMAL = 0; ACTBOSS = 1


class MODTYPE(IntEnum):
    FLAT = 0; ADDITIVE = 1; MULTIPLICATIVE = 2


class MODSOURCE(IntEnum):
    BASE = 0; ITEM = 1; ATTRIBUTE = 2; PASSIVE = 3; AccountStatus = 4; StatusEffect = 5
    BuffSkill = 6; ENVIRONMENT = 7


def name_map(enum_cls):
    return {m.value: m.name for m in enum_cls}
