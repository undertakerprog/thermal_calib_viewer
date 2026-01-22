#include "StdCalibTestWidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QTabWidget>
#include <QScrollArea>
#include <QTime>
#include <QLabel>
#include <QPushButton>
#include <QFileDialog>
#include <QListView>
#include <QTreeView>
#include <QComboBox>
#include <QDebug>
#include "iriscapture/core/mat_math.h"
#include "iriscapture/core/FpaImage.h"
#include "help_functions.h"
#include "iriscapture/Constants.h"
#include <iomanip>

#ifndef WIN32
#include <armadillo>
using namespace arma;
#endif

StdCalibTestWidget::StdCalibTestWidget(QWidget *parent) :
    QWidget(parent) {
    setWindowTitle("Standard calibration test results");

    tabWidget = new QTabWidget(this);
    auto vBoxLayout = new QVBoxLayout(this);

    QHBoxLayout * hBoxLayout = new QHBoxLayout();
    QPushButton * bOpen      = new QPushButton("Open");
    QPushButton * bClear     = new QPushButton("Clear");

    algMap.insert("Lienar", eye::imgproc::Algorithm::Linear);
    algMap.insert("Linear FS", eye::imgproc::Algorithm::LinearFullScale);
    algMap.insert("Linear DS", eye::imgproc::Algorithm::LinearDoubleScale);
    algMap.insert("LHE", eye::imgproc::Algorithm::LHE);

    cbAlgo = new QComboBox;
    cbAlgo->addItems({algMap.keyBegin(), algMap.keyEnd()});

    connect(bOpen, &QPushButton::clicked, this, &StdCalibTestWidget::open);
    connect(bClear, &QPushButton::clicked, this, [&]() {
        int idx = tabWidget->count() - 1;

        while (idx >= 0) {
            auto ptr = tabWidget->widget(idx);
            tabWidget->removeTab(idx);
            ptr->deleteLater();
            --idx;
        }
    });

    hBoxLayout->addWidget(bOpen);
    hBoxLayout->addWidget(bClear);
    hBoxLayout->addWidget(new QLabel("Algorithm: "));
    hBoxLayout->addWidget(cbAlgo);
    hBoxLayout->addStretch();

    vBoxLayout->addLayout(hBoxLayout);

    tabWidget->setTabsClosable(true);
    vBoxLayout->addWidget(tabWidget);

    this->setLayout(vBoxLayout);
    this->resize(800, 600);

    connect(tabWidget, &QTabWidget::tabCloseRequested, this, [&](int idx) {
        auto ptr = tabWidget->widget(idx);
        tabWidget->removeTab(idx);
        ptr->deleteLater();
    });
}

StdCalibTestWidget::~StdCalibTestWidget() {

}

void StdCalibTestWidget::createNewTab(const QString tabName, const QMap<double, QString> &fileNames) {
    QScrollArea * scrollArea = new QScrollArea;
    scrollArea->setWidget(new QWidget);
    scrollArea->setWidgetResizable(true);

    QGridLayout * grid = new QGridLayout;
    grid->setAlignment(Qt::AlignTop);
    scrollArea->widget()->setLayout(grid);

    scrollArea->setMinimumWidth(700);

    // ---------------------------------------

    QWidget * listWidget = new QWidget;
    listWidget->setLayout(new QVBoxLayout);

    QPushButton * bUpdate = new QPushButton("Update");
    QListView * listView  = new QListView;
    CalibFilesListModel * model = new CalibFilesListModel(fileNames);

    listView->setModel(model);
    listWidget->layout()->addWidget(listView);
    listWidget->layout()->addWidget(bUpdate);

    listWidget->setMaximumWidth(100);

    // ----------------------------------------

    QWidget * genWidget = new QWidget;
    genWidget->setLayout(new QHBoxLayout);

    QDoubleSpinBox * dsbFrom   = new QDoubleSpinBox;
    QDoubleSpinBox * dsbTo     = new QDoubleSpinBox;
    QDoubleSpinBox * dsbStep   = new QDoubleSpinBox;
    QSpinBox       * sbPolyN   = new QSpinBox;
    QPushButton    * bGenerate = new QPushButton("Generate");

    dsbFrom->setRange(-40.0, 100.0);
    dsbFrom->setValue(55.0);
    dsbFrom->setSingleStep(0.1);

    dsbTo->setRange(-40.0, 100.0);
    dsbTo->setValue(70.0);
    dsbTo->setSingleStep(0.1);

    dsbStep->setRange(0.1, 10.0);
    dsbStep->setValue(1.25);
    dsbStep->setSingleStep(0.1);

    sbPolyN->setRange(1, 10);
    sbPolyN->setValue(5);
    sbPolyN->setSingleStep(1);

    genWidget->layout()->addWidget(new QLabel("From: "));
    genWidget->layout()->addWidget(dsbFrom);
    genWidget->layout()->addWidget(new QLabel("To: "));
    genWidget->layout()->addWidget(dsbTo);
    genWidget->layout()->addWidget(new QLabel("Step: "));
    genWidget->layout()->addWidget(dsbStep);
    genWidget->layout()->addWidget(new QLabel("PolyN: "));
    genWidget->layout()->addWidget(sbPolyN);
    genWidget->layout()->addWidget(bGenerate);

    // ----------------------------------------

    QWidget * rightWidget = new QWidget;
    QCustomPlot * fpaTPlot = new QCustomPlot;

    rightWidget->setLayout(new QVBoxLayout);
    rightWidget->layout()->addWidget(fpaTPlot);
    rightWidget->layout()->addWidget(genWidget);

    fpaTPlot->setMinimumWidth(700);
    fpaTPlot->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);

    // ----------------------------------------

    QWidget * newTab = new QWidget;
    newTab->setLayout(new QHBoxLayout);
    newTab->layout()->addWidget(scrollArea);
    newTab->layout()->addWidget(listWidget);
    newTab->layout()->addWidget(rightWidget);

    tabWidget->addTab(newTab, tabName);

    // ----------------------------------------

    updateFpaTPlot(fpaTPlot, fileNames);
    calcTestImages(grid, fileNames);

    connect(bUpdate, &QPushButton::clicked, this, [ = ]() {
        calcTestImages(grid, model->getCheckedFiles());
    });

    connect(bGenerate, &QPushButton::clicked, this, [ = ]() {
        generateCalibs(model->getCheckedFiles(), dsbFrom->value(), dsbTo->value(), dsbStep->value(), sbPolyN->value());
    });
}

QStringList StdCalibTestWidget::getSelectedDirPaths(QString path) {
    QFileDialog* fileDialog = new QFileDialog(this, "Select Std calib sets for test...", path);
    fileDialog->setFileMode(QFileDialog::Directory);
    fileDialog->setOption(QFileDialog::DontUseNativeDialog, true);

    QListView *l = fileDialog->findChild<QListView*>("listView");

    if (l) {
        l->setSelectionMode(QAbstractItemView::MultiSelection);
    }

    QTreeView *t = fileDialog->findChild<QTreeView*>();

    if (t) {
        t->setSelectionMode(QAbstractItemView::MultiSelection);
    }

    fileDialog->exec();

    return fileDialog->selectedFiles();
}

void StdCalibTestWidget::setPath(QString path) {
    this->path = path;
}

void StdCalibTestWidget::open() {
    QStringList calibFolders = getSelectedDirPaths(path);

    for (auto & folder : calibFolders) {
        QMap<double, QString> calibFileNames;
        QStringList dirEntryList = QDir(folder).entryList({"*.raw"}, QDir::Filter::Files | QDir::Filter::NoDot | QDir::Filter::NoDotDot);

        for (const auto &entry : qAsConst(dirEntryList)) {
            auto nameParts = entry.split('_', Qt::SkipEmptyParts);
            bool isOk = false;
            double t = nameParts[1].toDouble(&isOk);

            if (!isOk) { // for old calib names
                uint16_t adc = nameParts.last().split(".", Qt::SkipEmptyParts).first().toInt();
                t = QString::number(ConvertAdcToCelcius(adc), 'f', 2).toDouble();
            }

            calibFileNames[t] = folder + "/" + entry;
        }

        createNewTab(QFileInfo(folder).fileName().split('.', Qt::SkipEmptyParts).first(), calibFileNames);
    }
}

void StdCalibTestWidget::calcTestImages(QGridLayout * grid, const QMap<double, QString> &calibFileNames) {
    clearWidgets(grid);

    if (calibFileNames.size() <= 3) {
        return;
    }

    auto prev = calibFileNames.begin();
    auto curr = prev + 1;
    auto next = curr + 1;

    int col = 0;
    int row = 0;

    while (next != calibFileNames.end()) {
        eye::FpaImage<int16_t> matPrev, matCurr, matNext, matCalib;
        matPrev.load(prev.value().toStdString());
        matCurr.load(curr.value().toStdString());
        matNext.load(next.value().toStdString());

        double prevWeight = (curr.key() - prev.key()) / (next.key() - prev.key());
        double nextWeight = 1 - prevWeight;

        eye::Math::blend(matPrev, prevWeight, matNext, nextWeight, matCalib, 15);
        eye::Math::sub(matCurr, eye::Math::min(matCurr));
        eye::Math::sub(matCurr, matCalib, matCurr);

        eye::Mat<uint8_t> matResult;
        matResult.create(matCurr);

        imageProcessorsManager.setAlgo(algMap[cbAlgo->currentText()]);
        imageProcessorsManager.process(matCurr, matResult);

        QImage grayImage((uchar *)matResult.first(), matResult.cols(), matResult.rows(), matResult.cols(), QImage::Format_Grayscale8);
        QImage rgbImage = grayImage.convertToFormat(QImage::Format_RGB888);

        QString imageName = QString::number(prev.key(), 'f', 2) + " | "
                            + QString::number(curr.key(), 'f', 2) + " | "
                            + QString::number(next.key(), 'f', 2) + "\n";

        QLabel * imgLabel = new QLabel;
        imgLabel->setPixmap(QPixmap::fromImage(rgbImage.scaled(320, 240)));
        imgLabel->setAlignment(Qt::AlignCenter);

        QLabel * textLabel = new QLabel{imageName};
        textLabel->setAlignment(Qt::AlignCenter);
        textLabel->setWordWrap(true);

        grid->addWidget(imgLabel, row * 2, col);
        grid->addWidget(textLabel, row * 2 + 1, col++);

        if (col >= maxCol) {
            col = 0;
            row++;
        }

        ++prev;
        ++curr;
        ++next;
    }
}

void StdCalibTestWidget::closeEvent(QCloseEvent *event) {
    emit windowClosed();
    event->accept();
}

void StdCalibTestWidget::clearWidgets(QLayout * layout) {
    if (!layout) {
        return;
    }

    while (auto item = layout->takeAt(0)) {
        clearWidgets(item->layout());
        item->widget()->deleteLater();
    }
}

void StdCalibTestWidget::updateFpaTPlot(QCustomPlot *plot, const QMap<double, QString> &fileNames) {

    plot->clearGraphs();

    plot->xAxis->setLabel("Calib number");
    plot->yAxis->setLabel("FPA temperature, C");
    plot->setInteractions(QCP::iRangeDrag | QCP::iRangeZoom | QCP::iSelectPlottables | QCP::iSelectLegend);
    plot->yAxis->setRange(-40, 80);

    QPen pen;
    pen.setColor(Qt::red);
    pen.setWidth(2);
    plot->addGraph();
    plot->graph()->setPen(pen);
    plot->graph()->setLineStyle(QCPGraph::LineStyle::lsLine);
    plot->graph()->setScatterStyle(QCPScatterStyle(QCPScatterStyle::ssDisc, 3));
    // plot->graph()->setName("Name");

    int i = 1;

    for (auto iter = fileNames.keyBegin(); iter != fileNames.keyEnd(); iter++, i++) {
        plot->graph()->addData(i, *iter);
    }

    plot->rescaleAxes();
    plot->replot();
}

void StdCalibTestWidget::generateCalibs(const QMap<double, QString> &fileNames, double from, double to, double step, int polyN) {
#ifndef WIN32

    QMap<double, eye::FpaImage<int16_t>> srcCalibSet;
    QVector<eye::FpaImage<int16_t>> genCalibSet;

    for (auto iter = fileNames.begin(); iter != fileNames.end(); iter++) {
        eye::FpaImage<int16_t> mat;

        if (mat.load(iter.value().toStdString())) {
            srcCalibSet.insert(iter.key(), std::move(mat));
        }
    }

    if (srcCalibSet.size() <= polyN + 1 || from >= to) {
        return;
    }

    int rows = srcCalibSet.first().rows();
    int cols = srcCalibSet.first().cols();
    int size = srcCalibSet.size();

    vec x, y, genX;
    uword n = polyN;
    int genCalibCount = (to - from) / step;

    x.resize(size);
    y.resize(size);
    genX.resize(genCalibCount);
    genCalibSet.resize(genCalibCount);

    for (uword i = 0; i < genX.size(); i++) {
        double t = from + i * step;
        genX[i] = t;
        genCalibSet[i].create(rows, cols);
        genCalibSet[i].tAdc = ConvertCelciusToAdc(t);
    }

    QProgressDialog progress("Downloading files...", "Abort", 0, rows);
    progress.setWindowModality(Qt::WindowModal);

    for (int row = 0; row < rows; row++) {
        progress.setValue(row);

        for (int col = 0; col < cols; col++) {
            int i = 0;

            for (auto iter = srcCalibSet.begin(); iter != srcCalibSet.end(); iter++, i++) {
                x[i] = iter.key();
                y[i] = *iter.value().at(row, col);
            }

            vec p;

            if (!polyfit(p, x, y, n)) {
                p.resize(n + 1);
                p.zeros();
            }

            vec genY = polyval(p, genX);

            for (unsigned i = 0; i < genY.size(); i++) {
                *genCalibSet[i].at(row, col) = genY[i];
            }
        }

        if (progress.wasCanceled()) {
            return;
        }
    }

    QFileInfo srcFilePath(fileNames.first());
    QString newDirPath = srcFilePath.dir().path() + ".(gen " + QString::number(from, 'f', 2) + "-" + QString::number(to, 'f', 2) + ")/";
    QDir newDir(newDirPath);

    newDir.mkpath(".");

    for (int i = 0; i < genCalibSet.size(); i++) {
        std::string name = eye::constants::CALIB_RUNTIME_FILE_NAME;
        std::stringstream ss;
        ss << eye::constants::CALIB_STD_FILE_PREFIX << "_" << std::setw(6) << std::setfill('_')
           << std::fixed << std::setprecision(2) << genX[i] << "_" << std::setprecision(0) << genCalibSet[i].tAdc << ".raw";
        name = newDirPath.toStdString() + ss.str();
        genCalibSet[i].save(name);
    }

    for (auto & filePath : fileNames) {
        QFileInfo fInfo(filePath);
        QString baseFileName = fInfo.completeBaseName();
        QString srcPath = fInfo.absoluteDir().path() + "/";

        QFile::copy(srcPath + baseFileName + ".raw", newDirPath + baseFileName + ".raw");
        QFile::copy(srcPath + baseFileName + ".txt", newDirPath + baseFileName + ".txt");
    }

#endif
}
