import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Target, Trophy, Users, Star, CheckCircle, Code, Zap, Shield, Globe, Award, TrendingUp, Sun, Moon, Menu, X, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useTheme } from 'next-themes';
import { cn } from '../lib/utils';
import { Logo } from '../components/Logo';

const Landing = () => {
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.pageYOffset > 10);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleTheme = () => {
    setTheme(isDark ? 'light' : 'dark');
  };

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    setMobileMenuOpen(false);
  };

  const features = [
    {
      icon: Code,
      title: "Interactive Practice",
      description: "Solve real system design problems with instant AI feedback."
    },
    {
      icon: Target,
      title: "Personalized Learning",
      description: "Get recommendations tailored to your skill level."
    },
    {
      icon: Trophy,
      title: "Track Progress",
      description: "Monitor your growth with detailed analytics."
    }
  ];

  const additionalFeatures = [
    {
      icon: Zap,
      title: "Lightning Fast",
      description: "Quick loading and seamless experience."
    },
    {
      icon: Shield,
      title: "Secure & Private",
      description: "Your data is protected with enterprise-grade security."
    },
    {
      icon: Globe,
      title: "Global Community",
      description: "Connect with engineers worldwide."
    }
  ];

  const benefits = [
    "Master system design fundamentals",
    "Build scalable architectures",
    "Get industry-ready skills",
    "Join a supportive community",
    "Access expert mentorship",
    "Earn recognized certificates"
  ];

  const testimonials = [
    {
      name: "Sarah Chen",
      role: "Software Engineer at Google",
      content: "SystemDesign.io helped me ace my system design interviews. The interactive approach is incredibly effective.",
      rating: 5
    },
    {
      name: "Marcus Johnson",
      role: "Senior Backend Engineer",
      content: "The personalized learning path made all the difference in mastering distributed systems.",
      rating: 5
    },
    {
      name: "Elena Rodriguez",
      role: "Solutions Architect",
      content: "Best platform for learning system design. The AI feedback is spot-on!",
      rating: 5
    }
  ];

  const stats = [
    { number: "50K+", label: "Active Learners", icon: Users },
    { number: "1M+", label: "Challenges Completed", icon: Target },
    { number: "95%", label: "Success Rate", icon: Trophy },
    { number: "24/7", label: "Community Support", icon: Globe }
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navigation */}
      <nav
        className={cn(
          "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
          isScrolled
            ? "bg-background/95 backdrop-blur-sm border-b border-border shadow-sm"
            : "bg-transparent"
        )}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 lg:h-20">
            {/* Logo */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              <Logo size={36} className="text-primary" />
              <span className="font-bold text-xl text-foreground">SystemDesign.io</span>
            </motion.div>

            {/* Center Navigation - Desktop */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="hidden lg:flex items-center gap-1"
            >
              {[
                { label: 'Home', action: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
                { label: 'Features', action: () => scrollToSection('features') },
                { label: 'Explore', action: () => navigate('/explore') },
                { label: 'About', action: () => scrollToSection('about') },
                { label: 'Contact', action: () => scrollToSection('contact') },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={item.action}
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors rounded-md"
                >
                  {item.label}
                </button>
              ))}
            </motion.div>

            {/* Right Side Buttons */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2"
            >
              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>

              {/* Mobile Menu Button */}
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden text-muted-foreground hover:text-foreground hover:bg-muted"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>

              {/* Sign In Button */}
              <Button
                onClick={() => navigate('/auth')}
                className="hidden sm:inline-flex bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm"
              >
                Sign In
              </Button>
            </motion.div>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="lg:hidden bg-background border-b border-border"
            >
              <div className="px-6 py-4 space-y-1">
                {[
                  { label: 'Home', action: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
                  { label: 'Features', action: () => scrollToSection('features') },
                  { label: 'Explore', action: () => navigate('/explore') },
                  { label: 'About', action: () => scrollToSection('about') },
                  { label: 'Contact', action: () => scrollToSection('contact') },
                ].map((item) => (
                  <button
                    key={item.label}
                    onClick={item.action}
                    className="block w-full text-left px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
                  >
                    {item.label}
                  </button>
                ))}
                <div className="pt-3 border-t border-border">
                  <Button
                    onClick={() => { navigate('/auth'); setMobileMenuOpen(false); }}
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                  >
                    Sign In
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-muted text-sm text-muted-foreground mb-8">
                <Zap className="w-4 h-4 text-primary" />
                <span>Powered by Agentic AI</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold text-foreground leading-tight mb-6">
                Master{' '}
                <span className="text-primary">System Design</span>
                <br className="hidden sm:block" />
                {' '}with AI Insights
              </h1>

              <p className="text-lg sm:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
                Practice real problems, get instant feedback from AI, and join a community of engineers mastering system design.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
            >
              <Button
                size="lg"
                onClick={() => navigate('/auth')}
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-6 text-lg font-medium shadow-lg hover:shadow-xl transition-all w-full sm:w-auto group"
              >
                Start Learning
                <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>

              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate('/explore')}
                className="border-2 border-border hover:border-primary hover:bg-primary/5 text-foreground px-8 py-6 text-lg font-medium transition-all w-full sm:w-auto"
              >
                Explore Problems
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
            </motion.div>

            {/* Hero Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-8"
            >
              {[
                { value: "50K+", label: "Engineers" },
                { value: "1000+", label: "Problems" },
                { value: "95%", label: "Success Rate" },
                { value: "4.9/5", label: "User Rating" },
              ].map((stat, i) => (
                <div key={i} className="p-4 rounded-xl border border-border">
                  <div className="text-2xl sm:text-3xl font-bold text-primary">{stat.value}</div>
                  <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 lg:py-32 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16 lg:mb-20"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Why Choose <span className="text-primary">SystemDesign.io</span>?
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              AI-powered learning meets proven methodologies for the best system design education.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -4 }}
                className="bg-background p-8 rounded-2xl border border-border hover:border-primary/50 hover:shadow-lg transition-all duration-300 group"
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary transition-colors duration-300">
                  <feature.icon className="w-6 h-6 text-primary group-hover:text-primary-foreground transition-colors duration-300" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Additional Features */}
      <section className="py-20 lg:py-32 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16 lg:mb-20"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Advanced <span className="text-primary">Features</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Powerful tools that make learning system design simple and effective.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            {additionalFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -4 }}
                className="p-8 rounded-2xl border border-border hover:border-primary/50 transition-all duration-300 group"
              >
                <div className="w-12 h-12 rounded-xl bg-background border border-border flex items-center justify-center mb-6 group-hover:border-primary transition-colors duration-300">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="about" className="py-20 lg:py-32 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
                What You'll <span className="text-primary">Achieve</span>
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Join thousands of engineers advancing their careers with SystemDesign.io.
              </p>
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <motion.div
                    key={benefit}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="w-4 h-4 text-primary" />
                    </div>
                    <span className="text-foreground">{benefit}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="border border-border p-8 lg:p-10 rounded-3xl"
            >
              <h3 className="text-2xl font-bold mb-6 text-foreground">Success Stories</h3>
              <div className="space-y-6">
                <div className="bg-primary/5 p-6 rounded-2xl">
                  <div className="flex items-center mb-3">
                    <Award className="w-5 h-5 mr-2 text-primary" />
                    <span className="font-semibold text-foreground">Career Growth</span>
                  </div>
                  <p className="text-muted-foreground text-sm sm:text-base">
                    "Landed my dream job at a top tech company after mastering system design with SystemDesign.io."
                  </p>
                </div>
                <div className="bg-primary/5 p-6 rounded-2xl">
                  <div className="flex items-center mb-3">
                    <TrendingUp className="w-5 h-5 mr-2 text-primary" />
                    <span className="font-semibold text-foreground">Skill Development</span>
                  </div>
                  <p className="text-muted-foreground text-sm sm:text-base">
                    "Improved my system design skills by 300% in just 6 months of consistent practice."
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 lg:py-32 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16 lg:mb-20"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Trusted by <span className="text-primary">Thousands</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Join our growing community of engineers and system design enthusiasts.
            </p>
          </motion.div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="p-6 sm:p-8 rounded-2xl text-center border border-border hover:border-primary/50 transition-colors"
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <stat.icon className="w-6 h-6 text-primary" />
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-foreground mb-1">{stat.number}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 lg:py-32 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16 lg:mb-20"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              What Our <span className="text-primary">Students</span> Say
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Real stories from real people who have transformed their careers.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={testimonial.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-background p-8 rounded-2xl border border-border hover:border-primary/50 transition-colors"
              >
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-primary fill-primary" />
                  ))}
                </div>
                <p className="text-muted-foreground mb-6 italic">"{testimonial.content}"</p>
                <div>
                  <div className="font-semibold text-foreground">{testimonial.name}</div>
                  <div className="text-primary text-sm">{testimonial.role}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32 px-6 lg:px-8 border-y border-border">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Ready to Start Your Journey?
            </h2>
            <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
              Join thousands of engineers who started with SystemDesign.io. Begin learning today.
            </p>
            <Button
              size="lg"
              onClick={() => navigate('/auth')}
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-10 py-6 text-lg font-medium shadow-lg hover:shadow-xl transition-all"
            >
              Get Started Now
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer id="contact" className="bg-background border-t border-border py-16 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
            <div className="sm:col-span-2 lg:col-span-1">
              <div className="flex items-center gap-3 mb-4">
                <Logo size={36} className="text-primary" />
                <span className="font-bold text-xl text-foreground">SystemDesign.io</span>
              </div>
              <p className="text-muted-foreground mb-6 max-w-sm">
                AI-powered system design practice with personalized feedback.
              </p>
              <div className="flex gap-3">
                {[
                  { icon: Globe, label: 'Website' },
                  { icon: Users, label: 'Community' },
                  { icon: Code, label: 'GitHub' },
                ].map((social, i) => (
                  <div
                    key={i}
                    className="w-10 h-10 rounded-lg border border-border hover:border-primary flex items-center justify-center cursor-pointer transition-colors group"
                  >
                    <social.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary-foreground transition-colors" />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4 text-foreground">Platform</h3>
              <ul className="space-y-3">
                {['Courses', 'Challenges', 'Community', 'Certificates'].map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="text-muted-foreground hover:text-primary transition-colors"
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4 text-foreground">Resources</h3>
              <ul className="space-y-3">
                {['Documentation', 'API Reference', 'Guides', 'Blog'].map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="text-muted-foreground hover:text-primary transition-colors"
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4 text-foreground">Support</h3>
              <ul className="space-y-3">
                {['Help Center', 'Contact Us', 'Privacy Policy', 'Terms of Service'].map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="text-muted-foreground hover:text-primary transition-colors"
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="border-t border-border mt-12 pt-8 text-center">
            <p className="text-muted-foreground">
              © 2025 SystemDesign.io. All rights reserved. Built for engineers.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
