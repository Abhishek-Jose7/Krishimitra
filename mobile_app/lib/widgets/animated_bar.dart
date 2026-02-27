import 'package:flutter/material.dart';

class AnimatedBar extends StatefulWidget {
  final double targetHeight;
  final Duration delay;
  final BoxDecoration decoration;
  
  const AnimatedBar({
    super.key,
    required this.targetHeight,
    required this.delay,
    required this.decoration,
  });

  @override
  State<AnimatedBar> createState() => _AnimatedBarState();
}

class _AnimatedBarState extends State<AnimatedBar> {
  double _currentHeight = 0.0;

  @override
  void initState() {
    super.initState();
    Future.delayed(widget.delay, () {
      if (mounted) {
        setState(() => _currentHeight = widget.targetHeight);
      }
    });
  }

  @override
  void didUpdateWidget(AnimatedBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.targetHeight != widget.targetHeight) {
      _currentHeight = widget.targetHeight;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 700),
      curve: Curves.easeInOut,
      height: _currentHeight,
      decoration: widget.decoration,
    );
  }
}
