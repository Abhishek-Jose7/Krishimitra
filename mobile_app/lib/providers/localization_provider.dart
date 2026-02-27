import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';

class LocalizationProvider extends ChangeNotifier {
  String _currentLanguage = 'en'; // Defaults to English. Options: 'en', 'hi', 'mr', 'kn'
  final FlutterTts _flutterTts = FlutterTts();

  String get currentLanguage => _currentLanguage;

  LocalizationProvider() {
    _initTts();
  }

  Future<void> _initTts() async {
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setPitch(1.0);
  }

  Future<void> setLanguage(String langCode) async {
    _currentLanguage = langCode;
    String ttsLang = 'en-US';
    switch (langCode) {
      case 'hi':
        ttsLang = 'hi-IN';
        break;
      case 'mr':
        ttsLang = 'mr-IN';
        break;
      case 'kn':
        ttsLang = 'kn-IN';
        break;
      case 'en':
      default:
        ttsLang = 'en-IN';
        break;
    }
    await _flutterTts.setLanguage(ttsLang);
    notifyListeners();
  }

  Future<void> speak(String text) async {
    await _flutterTts.stop();
    await _flutterTts.speak(text);
  }

  Future<void> stop() async {
    await _flutterTts.stop();
  }

  String translate(String key) {
    if (_currentLanguage == 'en') return _en[key] ?? key;
    if (_currentLanguage == 'hi') return _hi[key] ?? _en[key] ?? key;
    if (_currentLanguage == 'mr') return _mr[key] ?? _en[key] ?? key;
    if (_currentLanguage == 'kn') return _kn[key] ?? _en[key] ?? key;
    return key;
  }

  // --- ENGLISH ---
  final Map<String, String> _en = {
    'market_intelligence': 'Market Intelligence',
    'suggestion': 'Suggestion',
    'risk': 'Risk',
    'yield_estimate': 'Yield Estimate',
    'price_forecast': 'Price Forecast',
    'mandi_prices': 'Mandi Prices',
    'sell_hold_advice': 'Sell/Hold Advice',
    'now': 'Now',
    'later': 'Later',
    'pending': 'Pending',
    'sell_today': 'SELL TODAY',
    'hold_inventory': 'HOLD INVENTORY',
  };

  // --- HINDI ---
  final Map<String, String> _hi = {
    'market_intelligence': 'बाजार बुद्धिमत्ता',
    'suggestion': 'सुझाव',
    'risk': 'जोखिम',
    'yield_estimate': 'उपज का अनुमान',
    'price_forecast': 'कीमत का पूर्वानुमान',
    'mandi_prices': 'मंडी की कीमतें',
    'sell_hold_advice': 'बेचें/रोकें सलाह',
    'now': 'अभी',
    'later': 'बाद में',
    'pending': 'लंबित',
    'sell_today': 'आज ही बेचें',
    'hold_inventory': 'अभी रोक कर रखें',
  };

  // --- MARATHI ---
  final Map<String, String> _mr = {
    'market_intelligence': 'बाजार बुद्धिमत्ता',
    'suggestion': 'सल्ला',
    'risk': 'धोका',
    'yield_estimate': 'उत्पादनाचा अंदाज',
    'price_forecast': 'किंमतीचा अंदाज',
    'mandi_prices': 'मंडीचे भाव',
    'sell_hold_advice': 'विक्री/थांबण्याचा सल्ला',
    'now': 'आता',
    'later': 'नंतर',
    'pending': 'प्रलंबित',
    'sell_today': 'आजच विका',
    'hold_inventory': 'साठा ठेवा',
  };

  // --- KANNADA ---
  final Map<String, String> _kn = {
    'market_intelligence': 'ಮಾರುಕಟ್ಟೆ ಬುದ್ಧಿಮತ್ತೆ',
    'suggestion': 'ಸಲಹೆ',
    'risk': 'ಅಪಾಯ',
    'yield_estimate': 'ಇಳುವರಿ ಅಂದಾಜು',
    'price_forecast': 'ಬೆಲೆ ಮುನ್ಸೂಚನೆ',
    'mandi_prices': 'ಮಂಡಿ ಬೆಲೆಗಳು',
    'sell_hold_advice': 'ಮಾರಾಟ/ಹಿಡಿದಿಟ್ಟುಕೊಳ್ಳುವ ಸಲಹೆ',
    'now': 'ಈಗ',
    'later': 'ನಂತರ',
    'pending': 'ಬಾಕಿ ಉಳಿದಿದೆ',
    'sell_today': 'ಇಂದು ಮಾರಿ',
    'hold_inventory': 'ದಾಸ್ತಾನು ಇರಿಸಿ',
  };
}
