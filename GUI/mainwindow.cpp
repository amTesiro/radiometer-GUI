#include "mainwindow.h"
#include "ui_mainwindow.h"

MainWindow::MainWindow(QString python_path, QString scripts_path, QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    this->python_path = python_path;
    this->scripts_path = scripts_path;
    this->p = NULL;

    general_page = new GeneralPage(this);

    atmosphere_page = new AtmosPherePage(this);
    input_conf_page = new InputConfShow(this);
    aerosol_page = new AerosolPage(this);
    cloud_page = new CloudPage(this);
    //excel_page = new ExcelForm(this);
    trans_mode_page = new TransModelPage(this);

    this->wait_dialog = new WaitDialog(this);
    this->wait_dialog->hide();


    ui->tabWidget->addTab(general_page, QStringLiteral("主页"));
    ui->tabWidget->addTab(atmosphere_page, QStringLiteral("大气廓线"));
    ui->tabWidget->addTab(aerosol_page, QStringLiteral("气溶胶"));
    ui->tabWidget->addTab(cloud_page, QStringLiteral("水云和冰云"));
    ui->tabWidget->addTab(trans_mode_page, QStringLiteral("辐射传输计算模型"));
    ui->tabWidget->addTab(input_conf_page, QStringLiteral("显示输入项"));



    this->init_widget_list();

    connect(this->general_page, SIGNAL(GeneralSaveConfEvent(QString)),this,SLOT(on_general_page_conf_clicked(QString)));
    connect(this->general_page, SIGNAL(GeneralLoadConfEvent(QString)),this,SLOT(on_general_page_conf_load_clicked(QString)));
    connect(this->general_page, SIGNAL(GeneralSaveOutEvent(QString)),this,SLOT(on_general_page_out_clicked(QString)));
    connect(this->general_page, SIGNAL(GeneralSavePlotEvent(QString)),this,SLOT(on_general_page_plot_clicked(QString)));

}

MainWindow::~MainWindow()
{

    delete general_page;
    delete atmosphere_page;
    delete input_conf_page;
    delete aerosol_page;
    delete cloud_page;
    delete trans_mode_page;
        delete ui;
}

void MainWindow::init_widget_list()
{
    traversalControl_button(this->children(), this->button_list, string("QPushButton"));
    traversalControl_line(this->children(), this->edit_list, this->edit_map, string("QLineEdit"));
    traversalControl_box(this->children(), this->box_list, this->box_map, string("QComboBox"));
}

void MainWindow::get_input()
{
    //每次获取当前输入项之前，先清空map
    this->widget_map.clear();
    for(int index = 0; index < this->edit_list.size(); index ++)
    {
        if(this->edit_list[index] != NULL && !this->edit_list[index]->text().isEmpty())
        {
            QString option_name = this->edit_list[index]->property(string("option_name").c_str()).toString();
            qDebug() << option_name << this->edit_list[index]->text();
            this->widget_map[option_name] = this->edit_list[index]->text();
        }
    }
    for(int index = 0; index < this->box_list.size(); index ++)
    {
        if(this->box_list[index] != NULL && this->box_list[index]->currentText() != QString("off"))
        {
            QString option_name = this->box_list[index]->property(string("option_name").c_str()).toString();
            qDebug() << option_name << this->box_list[index]->currentText();
            this->widget_map[option_name] = this->box_list[index]->currentText();
        }
    }
}
QString MainWindow::get_output_str()
{
    this->get_input();

    QMap<QString, QString>::iterator iter = this->widget_map.begin();
    QString all_str;
    while (iter != this->widget_map.end())
    {
      QString tmp_str = iter.key() + QString(" ") + iter.value();
      all_str = all_str + tmp_str + QString("\n");
      iter++;
    }
    return all_str;
}
void MainWindow::load_conf(QString path)
{
    QVector<QString> line_list;
    this->clear_conf();

    this->read_conf(path, line_list);

    this->set_conf(line_list);
}

void MainWindow::read_conf(QString path, QVector<QString> &line_list)
{
    QFile file(path);
    file.open(QIODevice::ReadOnly|QIODevice::Text);
    QTextStream in(&file);
    while (!in.atEnd()) {
        QString line = in.readLine();
        line_list.append(line);
    }
    file.close();
}

QString MainWindow::read_all(QString path)
{
    QFile file(path);
    file.open(QIODevice::ReadOnly|QIODevice::Text);
    QTextStream in(&file);
    QString res_str = in.readAll();
    file.close();
    return res_str;
}
void MainWindow::clear_conf()
{
    for(int index = 0; index < this->box_list.size(); index++)
        this->box_list[index]->setCurrentIndex(0);
    for(int index = 0; index < this->edit_list.size(); index++)
        this->edit_list[index]->setText(QString());
}
void MainWindow::set_conf(QVector<QString> &line_list)
{
    for(int index = 0; index < line_list.size(); index++)
    {
        QStringList line_info = line_list[index].split(' ');
        if(line_info.size() < 2)
        {
            continue;
        }
        else
        {
            QString line_property = line_info.at(0);
            QString line_val = line_info.at(1);

            if(line_property.isEmpty() || line_val.isEmpty())
            {
                continue;
            }
            if(this->edit_map.contains(line_property))
            {
                this->edit_map[line_property]->setText(line_val);
            }
            else if(this->box_map.contains(line_property))
            {
                qDebug() << line_val;
                this->box_map[line_property]->setCurrentText(line_val);
            }
            else
            {
                continue;
            }
        }
    }
}

void MainWindow::on_general_page_conf_clicked(QString path)
{
    QFile file(path);
    file.open(QIODevice::WriteOnly|QIODevice::Text);
    QTextStream out(&file);
    out<<(this->get_output_str());
    file.close();
}
void MainWindow::on_general_page_conf_load_clicked(QString path)
{
    this->load_conf(path);
}

void MainWindow::call_python(QString out_path)
{
    QStringList args;
    this->p = new QProcess(this);
    args.append("-i");

    args.append(this->scripts_path);
    QString strArg;
    strArg.append(out_path);
    //strArg.append(QString("-i"));
    p->setNativeArguments(strArg);

    p->start(this->python_path, args);

    connect(p , SIGNAL(readyReadStandardOutput()) , this , SLOT(on_readoutput()));
}
void MainWindow::on_readoutput()
{
    qDebug()<<QString::fromLocal8Bit(this->p->readAllStandardError());

    QString out_str = this->read_all(this->std_out_path);

    p->close();
    p->waitForFinished();
    if(p != NULL)
        delete p;
    this->p = NULL;
    this->wait_dialog->set_init_status(false);
    this->wait_dialog->setText(out_str);

}


void MainWindow::on_general_page_out_clicked(QString path)
{

    QString qt_out_path = path + ".qt";
    QFile file(qt_out_path);
    file.open(QIODevice::WriteOnly|QIODevice::Text);
    QTextStream out(&file);
    out.setCodec("UTF-8");
    out<<(this->get_output_str());
    file.close();

    this->call_python(qt_out_path);

    this->std_out_path = qt_out_path + ".stdout";
    this->wait_dialog->set_init_status(true);
    this->wait_dialog->setModal(true);
    this->wait_dialog->exec();
}

void MainWindow::on_general_page_plot_clicked(QString path)
{
    qDebug() << path;
}

void MainWindow::on_tabWidget_currentChanged(int index)
{
    if(index == 5)
        this->input_conf_page->setInputConf(this->get_output_str());
}
