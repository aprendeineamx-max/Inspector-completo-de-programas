import QtQuick 6.5
import QtQuick.Controls 6.5
import QtQuick.Layouts
import QtQuick.Dialogs 6.5
import QtQuick.Controls.Material 6.5

ApplicationWindow {
    id: root
    width: 1200
    height: 780
    visible: true
    title: "Inspector Portable GUI"
    Material.theme: Material.Dark
    Material.accent: Material.Teal

    property string convertXmlPath: ""
    property string convertOutputPath: ""
    property string convertAppName: ""
    property string packageConfigPath: ""
    property string packageOutputDir: ""

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            spacing: 12
            Label {
                text: "Inspector Portable"
                font.bold: true
                font.pointSize: 13
                Layout.alignment: Qt.AlignVCenter
            }
            Label {
                text: "Flujo integral: Convertir XML → Crear paquete portable"
                font.bold: true
                Layout.alignment: Qt.AlignVCenter
            }
            Item { Layout.fillWidth: true }
            Label {
                id: statusLabel
                text: "Listo."
                color: "#c4f5ff"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            TabBar {
                id: tabBar
                Layout.fillWidth: true
                currentIndex: stack.currentIndex
                TabButton { text: "1. Convertir XML a JSON" }
                TabButton { text: "2. Generar paquete portable" }
            }

            StackLayout {
                id: stack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: tabBar.currentIndex

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 8

                            Label { text: "XML de traza" }
                            RowLayout {
                                spacing: 8
                                TextField {
                                    id: xmlInputField
                                Layout.fillWidth: true
                                text: root.convertXmlPath
                                placeholderText: "Selecciona el archivo exportado desde Uninstall Tool..."
                                onEditingFinished: root.convertXmlPath = text
                            }
                            Button {
                                text: "Examinar"
                                onClicked: xmlFileDialog.open()
                            }
                        }

                            Label { text: "Archivo JSON de salida" }
                            RowLayout {
                                spacing: 8
                                TextField {
                                    id: jsonOutputField
                                Layout.fillWidth: true
                                text: root.convertOutputPath
                                placeholderText: "Ruta donde guardar la configuración generada"
                                onEditingFinished: root.convertOutputPath = text
                            }
                            Button {
                                text: "Elegir"
                                onClicked: jsonFileDialog.open()
                            }
                        }

                            Label { text: "Nombre de la aplicación" }
                            TextField {
                                id: convertAppNameField
                                Layout.fillWidth: true
                                text: root.convertAppName
                            placeholderText: "Opcional (se usa el nombre del XML si se deja vacío)"
                            onEditingFinished: root.convertAppName = text
                        }
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        spacing: 12
                        Button {
                            text: "Abrir JSON generado"
                            enabled: backend.pathExists(jsonOutputField.text)
                            onClicked: backend.openPath(jsonOutputField.text)
                        }
                        Button {
                            text: "Convertir XML"
                            highlighted: true
                            onClicked: backend.convertXml(xmlInputField.text, jsonOutputField.text, convertAppNameField.text)
                        }
                    }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 8

                            Label { text: "Archivo de configuración JSON" }
                            RowLayout {
                                spacing: 8
                                TextField {
                                    id: configField
                                    Layout.fillWidth: true
                                    text: root.packageConfigPath
                                    placeholderText: "Selecciona el JSON a empaquetar"
                                    onEditingFinished: root.packageConfigPath = text
                                }
                                Button {
                                    text: "Examinar"
                                    onClicked: configDialog.open()
                                }
                            }

                            Label { text: "Carpeta de salida" }
                            RowLayout {
                                spacing: 8
                                TextField {
                                    id: outputField
                                    Layout.fillWidth: true
                                    text: root.packageOutputDir
                                    placeholderText: "Debe existir o crearse vacía"
                                    onEditingFinished: root.packageOutputDir = text
                                }
                                Button {
                                    text: "Seleccionar"
                                    onClicked: outputDirDialog.open()
                                }
                            }

                            Label { text: "Opciones" }
                            CheckBox {
                                id: dryRunCheck
                                text: "Dry-run (validar sin copiar archivos)"
                            }
                        }
                        RowLayout {
                            Layout.alignment: Qt.AlignRight
                            spacing: 12
                            Button {
                                text: "Abrir carpeta de salida"
                                onClicked: backend.openPath(outputField.text)
                            }
                            Button {
                                text: "Generar paquete"
                                highlighted: true
                                onClicked: backend.generatePackage(configField.text, outputField.text, dryRunCheck.checked)
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }

        GroupBox {
            title: "Registro de eventos"
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            ColumnLayout {
                anchors.fill: parent
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: logArea
                        readOnly: true
                        wrapMode: Text.Wrap
                    }
                }
                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    Button {
                        text: "Limpiar"
                        onClicked: logArea.text = ""
                    }
                }
            }
        }
    }

    Connections {
        target: backend
        function onOperationStarted(description) {
            statusLabel.text = description
        }
        function onOperationFinished(description) {
            statusLabel.text = description
            logArea.append("✔ " + description)
        }
        function onOperationFailed(error) {
            statusLabel.text = error
            logArea.append("✖ " + error)
        }
        function onLogMessage(message) {
            logArea.append(message)
        }
    }

    FileDialog {
        id: xmlFileDialog
        title: "Selecciona XML de traza"
        nameFilters: ["Archivos XML (*.xml)", "Todos los archivos (*)"]
        onAccepted: {
            root.convertXmlPath = backend.urlToLocalPath(selectedFile)
            xmlInputField.text = root.convertXmlPath
        }
    }

    FileDialog {
        id: jsonFileDialog
        title: "Guardar archivo JSON"
        nameFilters: ["Archivos JSON (*.json)", "Todos los archivos (*)"]
        onAccepted: {
            root.convertOutputPath = backend.urlToLocalPath(selectedFile)
            jsonOutputField.text = root.convertOutputPath
        }
    }

    FileDialog {
        id: configDialog
        title: "Selecciona archivo de configuración"
        nameFilters: ["JSON (*.json)", "Todos los archivos (*)"]
        onAccepted: {
            root.packageConfigPath = backend.urlToLocalPath(selectedFile)
            configField.text = root.packageConfigPath
        }
    }

    FolderDialog {
        id: outputDirDialog
        title: "Selecciona carpeta destino"
        onAccepted: {
            root.packageOutputDir = backend.urlToLocalPath(selectedFolder)
            outputField.text = root.packageOutputDir
        }
    }
}
