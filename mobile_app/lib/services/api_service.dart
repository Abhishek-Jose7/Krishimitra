import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';

class ApiService {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:5000';
    }
    return 'http://10.0.2.2:5000';
  }

  // ── Yield ──
  Future<Map<String, dynamic>> predictYield(Map<String, dynamic> data) async {
    return _post('/yield/predict', data);
  }

  // ── Price Forecast ──
  Future<Map<String, dynamic>> forecastPrice(String crop, String mandi, {String? state}) async {
    final stateParam = state != null && state.isNotEmpty ? '&state=$state' : '';
    final response = await http.get(
      Uri.parse('$baseUrl/price/forecast?crop=$crop&mandi=$mandi$stateParam'),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load forecast');
    }
  }

  // ── Recommendation / Sell-Hold Advice ──
  Future<Map<String, dynamic>> getRecommendation(Map<String, dynamic> data) async {
    return _post('/recommendation', data);
  }

  // ── Mandi Prices ──
  Future<List<dynamic>> getMandiPrices(String crop, {String? district}) async {
    String url = '$baseUrl/mandi/prices?crop=$crop';
    if (district != null) url += '&district=$district';
    final response = await http.get(Uri.parse(url));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load mandi prices');
    }
  }

  // ── Market Risk ──
  Future<Map<String, dynamic>> getMarketRisk() async {
    final response = await http.get(Uri.parse('$baseUrl/mandi/risk'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load market risk');
    }
  }

  // ── Weather ──
  Future<Map<String, dynamic>> getWeather(String district) async {
    final response = await http.get(
      Uri.parse('$baseUrl/weather?district=$district'),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load weather');
    }
  }

  // ── Farmer Profile ──
  Future<Map<String, dynamic>> registerFarmer(Map<String, dynamic> data) async {
    return _post('/farmer/register', data);
  }

  Future<Map<String, dynamic>> getProfile(int id) async {
    final response = await http.get(Uri.parse('$baseUrl/farmer/$id'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load profile');
    }
  }

  // ── Actual Yield Feedback ──
  Future<Map<String, dynamic>> submitActualYield(double actualProduction) async {
    return _post('/yield/actual', {'actual_production': actualProduction});
  }

  // ── Intelligent Dashboard (single call) ──
  Future<Map<String, dynamic>> postIntelligentDashboard(Map<String, dynamic> data) async {
    return _post('/dashboard/intelligent', data);
  }

  // ── Password Auth ──
  Future<Map<String, dynamic>> registerWithPassword({
    required String phone,
    required String password,
    String? name,
  }) async {
    return _post('/auth/register', {
      'phone': phone,
      'password': password,
      if (name != null) 'name': name,
    });
  }

  Future<Map<String, dynamic>> loginWithPassword({
    required String phone,
    required String password,
  }) async {
    return _post('/auth/login', {
      'phone': phone,
      'password': password,
    });
  }

  // ── Private Helpers ──
  Future<Map<String, dynamic>> _post(String endpoint, Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl$endpoint'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(data),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        // Parse error message from response body if available
        try {
          final errorBody = json.decode(response.body);
          throw Exception(errorBody['error'] ?? 'Request failed: ${response.statusCode}');
        } catch (_) {
          throw Exception('Request failed: ${response.statusCode} - ${response.body}');
        }
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Network error: $e');
    }
  }
}

