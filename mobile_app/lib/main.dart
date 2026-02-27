import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'theme.dart';
import 'services/api_service.dart';
import 'providers/farmer_profile_provider.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding/welcome_screen.dart';

void main() {
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
  };
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => ApiService()),
        ChangeNotifierProvider<FarmerProfile>(create: (_) => FarmerProfile()),
      ],
      child: MaterialApp(
        title: 'KrishiMitra AI',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: const SplashRouter(),
      ),
    );
  }
}

/// Splash/Router: Loads profile from local storage and routes accordingly.
///  - If onboarding is complete → HomeScreen (Dashboard)
///  - If not → LanguageScreen (start onboarding)
class SplashRouter extends StatefulWidget {
  const SplashRouter({super.key});

  @override
  State<SplashRouter> createState() => _SplashRouterState();
}

class _SplashRouterState extends State<SplashRouter> {
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    await profile.loadFromLocal();

    if (mounted) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        backgroundColor: AppTheme.primaryGreen,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.eco, color: Colors.white, size: 44),
              ),
              const SizedBox(height: 20),
              Text(
                "KrishiMitra",
                style: AppTheme.headingLarge.copyWith(
                  color: Colors.white,
                  fontSize: 28,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                "Your Smart Farming Partner",
                style: AppTheme.bodyMedium.copyWith(
                  color: Colors.white70,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 32),
              const CircularProgressIndicator(
                color: Colors.white,
                strokeWidth: 2,
              ),
            ],
          ),
        ),
      );
    }

    final profile = Provider.of<FarmerProfile>(context);

    if (profile.onboardingComplete) {
      return const HomeScreen();
    } else {
      return const WelcomeScreen();
    }
  }
}
