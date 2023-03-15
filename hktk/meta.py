from enum import Enum, EnumMeta, unique
import hktk.data_objects as data_objects
from typing import Type
from dataclasses import dataclass
from functools import partial


@dataclass(frozen=True)
class RecordType:
    name: str
    analytic_cls: Type[data_objects.AnalyticRecordList]


CumulativeRecordType = partial(RecordType, analytic_cls=data_objects.CumulativeTypeRecordList)
ArrayRecordType = partial(RecordType, analytic_cls=data_objects.ArrayTypeRecordList)
CategoricalRecordType = partial(RecordType, analytic_cls=data_objects.CategoricalTypeRecordList)
EventRecordType = partial(RecordType, analytic_cls=data_objects.EventTypeRecordList)
SummaryArrayRecordType = partial(RecordType, analytic_cls=data_objects.SummaryArrayTypeRecordList)


class RecordTypesMeta(EnumMeta):
    def __getitem__(self, hk_type: str) -> RecordType:
        try:
            ret = super().__getitem__(hk_type).value
        except KeyError:
            ret = RecordType(hk_type, data_objects.InvalidTypeRecordList)
        return ret


@unique
class RecordTypes(Enum, metaclass=RecordTypesMeta):
    HKQuantityTypeIdentifierActiveEnergyBurned = CumulativeRecordType('ActiveEnergyBurned')
    HKQuantityTypeIdentifierBasalEnergyBurned = CumulativeRecordType('BasalEnergyBurned')
    HKQuantityTypeIdentifierDistanceCycling = CumulativeRecordType('DistanceCycling')
    HKQuantityTypeIdentifierDistanceWalkingRunning = CumulativeRecordType('DistanceWalkingRunning')
    HKQuantityTypeIdentifierStepCount = CumulativeRecordType('StepCount')
    HKQuantityTypeIdentifierAppleExerciseTime = CumulativeRecordType('AppleExerciseTime')
    HKQuantityTypeIdentifierAppleStandTime = CumulativeRecordType('AppleStandTime')
    HKQuantityTypeIdentifierFlightsClimbed = CumulativeRecordType('FlightsClimbed')
    HKQuantityTypeIdentifierDietaryCaffeine = RecordType('DietaryCaffeine', data_objects.CaffeineIntakeRecordList)
    HKQuantityTypeIdentifierNumberOfAlcoholicBeverages = CumulativeRecordType('NumberOfAlcoholicBeverages')
    HKQuantityTypeIdentifierNumberOfTimesFallen = CumulativeRecordType('NumberOfTimesFallen')

    HKQuantityTypeIdentifierHeartRate = ArrayRecordType('HeartRate')
    HKQuantityTypeIdentifierWalkingSpeed = ArrayRecordType('WalkingSpeed')
    HKQuantityTypeIdentifierWalkingStepLength = ArrayRecordType('WalkingStepLength')
    HKQuantityTypeIdentifierWalkingDoubleSupportPercentage = ArrayRecordType('WalkingDoubleSupportPercentage')
    HKQuantityTypeIdentifierRespiratoryRate = ArrayRecordType('RespiratoryRate')
    HKQuantityTypeIdentifierEnvironmentalAudioExposure = ArrayRecordType('EnvironmentalAudioExposure')
    HKQuantityTypeIdentifierHeadphoneAudioExposure = ArrayRecordType('HeadphoneAudioExposure')
    HKQuantityTypeIdentifierWalkingAsymmetryPercentage = ArrayRecordType('WalkingAsymmetryPercentage')
    HKQuantityTypeIdentifierOxygenSaturation = ArrayRecordType('OxygenSaturation')
    HKQuantityTypeIdentifierBloodPressureSystolic = ArrayRecordType('BloodPressureSystolic')
    HKQuantityTypeIdentifierBloodPressureDiastolic = ArrayRecordType('BloodPressureDiastolic')
    HKQuantityTypeIdentifierHeartRateVariabilitySDNN = ArrayRecordType('HeartRateVariabilitySDNN')
    HKQuantityTypeIdentifierEnvironmentalSoundReduction = ArrayRecordType('EnvironmentalSoundReduction')
    HKQuantityTypeIdentifierStairAscentSpeed = ArrayRecordType('StairAscentSpeed')
    HKQuantityTypeIdentifierStairDescentSpeed = ArrayRecordType('StairDescentSpeed')
    HKQuantityTypeIdentifierWalkingHeartRateAverage = ArrayRecordType('WalkingHeartRateAverage')
    HKQuantityTypeIdentifierAppleSleepingWristTemperature = ArrayRecordType('AppleSleepingWristTemperature')
    HKQuantityTypeIdentifierBodyTemperature = ArrayRecordType('BodyTemperature')
    HKQuantityTypeIdentifierRestingHeartRate = ArrayRecordType('RestingHeartRate')

    HKCategoryTypeIdentifierAppleStandHour = CategoricalRecordType('AppleStandHour')
    HKCategoryTypeIdentifierSleepAnalysis = RecordType('SleepAnalysis', data_objects.SleepStageRecordList)

    HKCategoryTypeIdentifierHandwashingEvent = EventRecordType('HandwashingEvent')
    HKCategoryTypeIdentifierAudioExposureEvent = EventRecordType('AudioExposureEvent')
    HKCategoryTypeIdentifierMindfulSession = EventRecordType('MindfulSession')
    HKCategoryTypeIdentifierSkippedHeartbeat = EventRecordType('SkippedHeartbeat')
    HKCategoryTypeIdentifierLowHeartRateEvent = EventRecordType('LowHeartRateEvent')
    HKCategoryTypeIdentifierHighHeartRateEvent = EventRecordType('HighHeartRateEvent')
    HKCategoryTypeIdentifierAbdominalCramps = EventRecordType('AbdominalCramps')
    HKCategoryTypeIdentifierChestTightnessOrPain = EventRecordType('ChestTightnessOrPain')
    HKCategoryTypeIdentifierLowCardioFitnessEvent = EventRecordType('LowCardioFitnessEvent')

    HKQuantityTypeIdentifierBodyMassIndex = SummaryArrayRecordType('BodyMassIndex')
    HKQuantityTypeIdentifierBodyMass = SummaryArrayRecordType('BodyMass')
    HKQuantityTypeIdentifierBodyFatPercentage = SummaryArrayRecordType('BodyFatPercentage')
    HKQuantityTypeIdentifierLeanBodyMass = SummaryArrayRecordType('LeanBodyMass')
    HKQuantityTypeIdentifierAppleWalkingSteadiness = SummaryArrayRecordType('AppleWalkingSteadiness')
    HKQuantityTypeIdentifierVO2Max = SummaryArrayRecordType('VO2Max')
    HKQuantityTypeIdentifierHeartRateRecoveryOneMinute = SummaryArrayRecordType('HeartRateRecoveryOneMinute')
    HKQuantityTypeIdentifierHeight = SummaryArrayRecordType('Height')
    HKQuantityTypeIdentifierSixMinuteWalkTestDistance = SummaryArrayRecordType('SixMinuteWalkTestDistance')

    HKDataTypeSleepDurationGoal = RecordType('SleepDurationGoal', data_objects.InvalidTypeRecordList)
