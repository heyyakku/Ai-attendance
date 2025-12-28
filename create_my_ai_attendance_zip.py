#!/usr/bin/env python3
# create_my_ai_attendance_zip.py
# Run: python create_my_ai_attendance_zip.py
# Produces: my_ai_attendance.zip with Flutter project skeleton.

import os, pathlib, zipfile, shutil, textwrap

BASE_DIR = pathlib.Path.cwd() / "my_ai_attendance"
ZIP_PATH = pathlib.Path.cwd() / "my_ai_attendance.zip"

# Reset folder if exists
if BASE_DIR.exists():
    shutil.rmtree(BASE_DIR)
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Helper function to write files
def write(path, content):
    p = BASE_DIR / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# ------------------------------
# pubspec.yaml
# ------------------------------
write("pubspec.yaml", textwrap.dedent("""\
name: my_ai_attendance
description: Premium Neon UI Attendance app
publish_to: "none"
version: 1.0.0+1

environment:
  sdk: ">=2.17.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter
  provider: ^6.0.5
  http: ^0.13.6
  camera: ^0.10.0+4
  permission_handler: ^10.4.0
  flutter_spinkit: ^5.1.0
  animations: ^2.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
  assets:
    - assets/
"""))


# ------------------------------
# lib/main.dart
# ------------------------------
write("lib/main.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'routes.dart';
import 'theme.dart';
import 'services/api_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Provider<ApiService>(
      create: (_) => ApiService(baseUrl: 'http://192.168.31.105:5000'), // your Flask base URL
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'AI Attendance',
        theme: neonTheme,
        initialRoute: '/',
        routes: appRoutes,
      ),
    );
  }
}
"""))


# ------------------------------
# lib/theme.dart
# ------------------------------
write("lib/theme.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';

final Color accent = Color(0xFF4C8CFF);
final Color neonBg = Color(0xFF050B1A);

final ThemeData neonTheme = ThemeData.dark().copyWith(
  scaffoldBackgroundColor: neonBg,
  primaryColor: accent,
  colorScheme: ColorScheme.dark(primary: accent, secondary: accent),
);
"""))


# ------------------------------
# lib/routes.dart
# ------------------------------
write("lib/routes.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';
import 'pages/login_page.dart';
import 'pages/dashboard_page.dart';
import 'pages/camera_page.dart';

final Map<String, WidgetBuilder> appRoutes = {
  '/': (ctx) => LoginPage(),
  '/dashboard': (ctx) => DashboardPage(),
  '/camera': (ctx) => CameraPage(),
};
"""))


# ------------------------------
# lib/services/api_service.dart
# ------------------------------
write("lib/services/api_service.dart", textwrap.dedent("""\
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl;
  ApiService({required this.baseUrl});

  Future<Map<String, dynamic>> login(String user, String pass) async {
    final res = await http.post(
      Uri.parse('$baseUrl/login'),
      body: {'username': user, 'password': pass},
    );
    return {'statusCode': res.statusCode, 'body': res.body};
  }
}
"""))


# ------------------------------
# NeonCard Widget
# ------------------------------
write("lib/widgets/neon_card.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';

class NeonCard extends StatelessWidget {
  final Widget child;
  const NeonCard({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white24),
      ),
      child: child,
    );
  }
}
"""))


# ------------------------------
# Login Page
# ------------------------------
write("lib/pages/login_page.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../widgets/neon_card.dart';

class LoginPage extends StatefulWidget {
  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final userCtrl = TextEditingController();
  final passCtrl = TextEditingController();

  bool loading = false;

  void doLogin() async {
    final api = Provider.of<ApiService>(context, listen: false);

    setState(() => loading = true);

    final res = await api.login(userCtrl.text.trim(), passCtrl.text.trim());

    setState(() => loading = false);

    if (res['statusCode'] == 200) {
      Navigator.pushReplacementNamed(context, '/dashboard');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Login Failed")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: NeonCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text("Login", style: TextStyle(fontSize: 22)),
              SizedBox(height: 20),
              TextField(controller: userCtrl, decoration: InputDecoration(hintText: "Username")),
              SizedBox(height: 10),
              TextField(controller: passCtrl, decoration: InputDecoration(hintText: "Password"), obscureText: true),
              SizedBox(height: 20),
              loading
                  ? CircularProgressIndicator()
                  : ElevatedButton(onPressed: doLogin, child: Text("Login")),
            ],
          ),
        ),
      ),
    );
  }
}
"""))


# ------------------------------
# Dashboard Page
# ------------------------------
write("lib/pages/dashboard_page.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';
import '../widgets/neon_card.dart';

class DashboardPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Admin Dashboard")),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: NeonCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Today: ${DateTime.now().toString().split(' ')[0]}"),
              SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => Navigator.pushNamed(context, '/camera'),
                child: Text("Mark Attendance (Camera)"),
              )
            ],
          ),
        ),
      ),
    );
  }
}
"""))


# ------------------------------
# Camera Page
# ------------------------------
write("lib/pages/camera_page.dart", textwrap.dedent("""\
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';

class CameraPage extends StatefulWidget {
  @override
  _CameraPageState createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> {
  CameraController? controller;
  bool initialized = false;

  @override
  void initState() {
    super.initState();
    initCamera();
  }

  Future<void> initCamera() async {
    await Permission.camera.request();

    final cameras = await availableCameras();
    controller = CameraController(cameras[0], ResolutionPreset.medium);
    await controller!.initialize();

    setState(() => initialized = true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Camera")),
      body: Center(
        child: initialized
            ? CameraPreview(controller!)
            : CircularProgressIndicator(),
      ),
    );
  }
}
"""))


# ------------------------------
# README + assets folder
# ------------------------------
write("README.md", "AI Attendance Flutter App (Auto-generated)\n")
write("assets/README.txt", "Put your images here\n")

# Create android & ios placeholder folders
(BASE_DIR / "android").mkdir(exist_ok=True)
(BASE_DIR / "ios").mkdir(exist_ok=True)

# ------------------------------
# ZIP the whole project
# ------------------------------
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for file in sorted(BASE_DIR.rglob("*")):
        z.write(file, file.relative_to(BASE_DIR.parent))

print("DONE! ZIP created:", ZIP_PATH)
