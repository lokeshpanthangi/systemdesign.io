import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/authService';
import { useToast } from '@/hooks/use-toast';
import AuthSwitch from '@/components/ui/auth-switch';

const Auth = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleLogin = async ({ email, password }: any) => {
    if (!email || !password) {
      toast({
        title: 'Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    try {
      await authService.login(email, password);

      toast({
        title: 'Success',
        description: 'Logged in successfully!',
      });

      navigate('/dashboard');
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Authentication failed',
        variant: 'destructive',
      });
    }
  };

  const handleSignup = async ({ firstName, lastName, email, password }: any) => {
    if (!firstName || !email || !password) {
      toast({
        title: 'Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    try {
      await authService.signup({
        first_name: firstName,
        last_name: lastName || "",
        email: email,
        password: password,
      });

      toast({
        title: 'Success',
        description: 'Account created successfully! Please sign in.',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Authentication failed',
        variant: 'destructive',
      });
    }
  };

  const handleGoogleAuth = () => {
    toast({
      title: 'Coming Soon',
      description: 'Google authentication will be available soon!',
    });
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* Back button floats above everything */}
      <Button 
        variant="ghost" 
        onClick={() => navigate('/')} 
        className="absolute top-6 left-6 z-[100] hover:bg-white/20 text-white hover:text-white"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <AuthSwitch 
        onLogin={handleLogin} 
        onSignup={handleSignup} 
        onGoogleAuth={handleGoogleAuth}
      />
    </div>
  );
};

export default Auth;
