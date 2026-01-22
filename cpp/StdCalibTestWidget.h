#ifndef STDCALIBTESTWIDGET_H
#define STDCALIBTESTWIDGET_H

#include <QWidget>
#include <QCloseEvent>
#include <QVBoxLayout>
#include <QTabWidget>
#include <QComboBox>
#include <QStringListModel>
#include "qcustomplot/qcustomplot.h"
#include "iriscapture/imgproc/ImageProcessorsManager.h"

class CalibFilesListModel : public QStringListModel {
public:

    QSet<QPersistentModelIndex> uncheckedItems;
    QMap<double, QString> calibFiles;

    CalibFilesListModel(const QMap<double, QString> &map, QObject* parent = 0) : QStringListModel(parent) {
        calibFiles = map;
        QStringList sl;

        for (auto & key : map.keys()) {
            sl.append(QString::number(key, 'f', 2));
        }

        setStringList(sl);
    }

    Qt::ItemFlags flags (const QModelIndex & index) const {
        Qt::ItemFlags defaultFlags = QStringListModel::flags(index);

        if (index.isValid()) {
            return defaultFlags | Qt::ItemIsUserCheckable;
        }

        return defaultFlags;
    }

    bool setData(const QModelIndex &index, const QVariant &value, int role) {
        if (!index.isValid() || role != Qt::CheckStateRole) {
            return false;
        }

        if (value == Qt::Unchecked) {
            uncheckedItems.insert(index);
        } else {
            uncheckedItems.remove(index);
        }

        emit dataChanged(index, index);
        return true;
    }

    QVariant data(const QModelIndex &index, int role) const {
        if (!index.isValid()) {
            return QVariant();
        }

        if (role == Qt::CheckStateRole) {
            return uncheckedItems.contains(index) ? Qt::Unchecked : Qt::Checked;
        }

        return QStringListModel::data(index, role);
    }

    QMap<double, QString> getCheckedFiles() {
        QMap<double, QString> map(calibFiles);

        for (auto & item : uncheckedItems) {
            map.remove(data(item, Qt::DisplayRole).toDouble());
        }

        return map;
    }
};

class StdCalibTestWidget : public QWidget {
    Q_OBJECT

    int maxCol = 2;
    QString path;
    QTabWidget * tabWidget;
    QComboBox  * cbAlgo;
    QMap<QString, eye::imgproc::Algorithm> algMap;

    eye::imgproc::ImageProcessorsManager imageProcessorsManager;

    void createNewTab(const QString tabName, const QMap<double, QString> & fileNames);
    QStringList getSelectedDirPaths(QString path);
    void clearWidgets(QLayout * layout);
    void updateFpaTPlot(QCustomPlot *plot, const QMap<double, QString> & fileNames);
    void generateCalibs(const QMap<double, QString> & fileNames, double from, double to, double step, int polyN);

protected:
    virtual void closeEvent(QCloseEvent * event) override;

public:
    explicit StdCalibTestWidget(QWidget *parent = nullptr);
    ~StdCalibTestWidget();

    void setPath(QString path);
    void open();
    void calcTestImages(QGridLayout *grid, const QMap<double, QString> &calibFileNames);

signals:
    void windowClosed();
};

#endif // STDCALIBTESTWIDGET_H
