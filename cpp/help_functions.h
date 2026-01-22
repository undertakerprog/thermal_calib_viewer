#ifndef HELP_FUNCTIONS_H
#define HELP_FUNCTIONS_H

#include <QVector>
#include <QColor>
#include <cmath>

enum PicoFpaMode {
    MODE_SDR             =  0,
    MODE_DDR             =  8,
    MODE_SDR_16K         =  16,
    MODE_SDR_INVERT      =  32,
    MODE_SDR_INVERT_16K  =  48
};

enum AdcVersion {
    v1 = 1,
    v2,
    v3
};

inline QVector<QColor> rndColors(int count) {
    QVector<QColor> colors;
    double currentHue = 0.0;

    for (int i = 0; i < count; i++) {
        colors.push_back( QColor::fromHslF(currentHue, 1.0, 0.5) );
        currentHue += 0.618033988749895;
        currentHue = std::fmod(currentHue, 1.0f);
    }

    return colors;
}

inline double ConvertAdcToVoltage(uint16_t adc_value, PicoFpaMode mode = MODE_SDR_INVERT_16K, AdcVersion verAdc = v2) {
    uint16_t adc_max_value = (mode & MODE_SDR_16K) ? (INT16_MAX >> 1) : (INT16_MAX >> 2);

    if (!(mode & PicoFpaMode::MODE_SDR_INVERT)) {
        adc_value = adc_max_value - adc_value;
    }

    double adc_to_v = 2.0 / adc_max_value;
    double v_adc = adc_value * adc_to_v + 0.5;

    if (verAdc == AdcVersion::v2) {
        return (v_adc - 0.6) * 2.4 / 1.8 + 0.5;
    }

    return v_adc;
}

inline uint16_t ConvertVoltageToAdc(double v_adc, PicoFpaMode mode = MODE_SDR_INVERT_16K, AdcVersion verAdc = v2) {
    if (verAdc == AdcVersion::v2) {
        v_adc = ((v_adc - 0.5) * 0.75) + 0.6;
    }

    uint16_t adc_max_value = (mode & MODE_SDR_16K) ? (INT16_MAX >> 1) : (INT16_MAX >> 2);
    double adc_to_v = 2.0 / adc_max_value;
    uint16_t adc_value = (v_adc - 0.5) / adc_to_v;

    if (!(mode & PicoFpaMode::MODE_SDR_INVERT)) {
        adc_value = adc_max_value - adc_value;
    }

    return adc_value;
}

inline double ConvertAdcToCelcius(uint16_t adc_value, PicoFpaMode mode = MODE_SDR_INVERT_16K, AdcVersion verAdc = v2) {
    double v = ConvertAdcToVoltage(adc_value, mode, verAdc);
    return -207.9 * v + 478.17;
}

inline uint16_t ConvertCelciusToAdc(double tC, PicoFpaMode mode = MODE_SDR_INVERT_16K, AdcVersion verAdc = v2) {
    double v = (tC - 478.17) / (-207.9);
    return ConvertVoltageToAdc(v, mode, verAdc);
}

//void saveAsPgm(const eye::Mat<int16_t> &mat, QString path) {
//    QByteArray ba;
//    ba.append(reinterpret_cast<char *>(mat.first()), mat.size());

//    qint16 *p    = reinterpret_cast<qint16 *>(ba.data());
//    qint16 *pEnd = reinterpret_cast<qint16 *>(ba.data()) + mat.total();
//    qint16 min = INT16_MAX;
//    qint16 max = INT16_MIN;

//    while (p < pEnd) {
//        min = *p < min ? *p : min;
//        max = *p > max ? *p : max;
//        ++p;
//    }

//    QFile pgmFile(path + ".pgm");

//    if (!pgmFile.open(QIODevice::WriteOnly)) {
//        qDebug () << "cannot create pgm file";
//        return;
//    }

//    QString pgmHeader("P5\n%1 %2\n%3\n");
//    pgmHeader = pgmHeader.arg(mat.cols()).arg(mat.rows()).arg(max - min);
//    pgmFile.write(pgmHeader.toLocal8Bit());

//    p    = reinterpret_cast<qint16 *>(ba.data());
//    pEnd = reinterpret_cast<qint16 *>(ba.data()) + mat.total();

//    while (p < pEnd) {
//        *p -= min;
//        qint16 t = *p;
//        *p <<= 8;
//        *p += t >> 8;
//        ++p;
//    }

//    pgmFile.write(ba);
//    pgmFile.close();
//}

#endif // HELP_FUNCTIONS_H
