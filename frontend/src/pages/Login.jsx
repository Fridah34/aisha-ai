//========================================================================
//  LOGIN INTERACTIVE USER VISUAL FORM
//========================================================================

import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Mail, Eye, EyeOff } from 'lucide-react';

const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

// const tells the computer: "Create a labeled box for this data, and never let its name or purpose change."
export default function Login() {
    const navigate = useNavigate();
    const location = useLocation();

    const { login, loading, error } = useAuth();

    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const [showPassword, setShowPassword] = useState(false);
    const [formErrors, setFormErrors] = useState('');

    // Success message passed from Signup page
    const [successMessage, setSuccessMessage] = useState(
        location.state?.message || ''
    );

    const targetRedirectPath =
        location.state?.from?.pathname || '/overview';

    // Remove success message after 5 seconds
    useEffect(() => {
        if (!successMessage) return;

        const timer = setTimeout(() => {
            setSuccessMessage('');
        }, 5000);

        return () => clearTimeout(timer);
    }, [successMessage]);

    //========================================================================
    // HANDLE INPUT CHANGES
    //========================================================================
    const handleChange = (e) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.name]: e.target.value,
        }));

        setFormErrors('');
    };

    //========================================================================
    // FORM SUBMISSION
    //========================================================================
    const handleSubmit = async (e) => {
        e.preventDefault();

        setFormErrors('');

        const email = formData.email.trim();
        const password = formData.password;

        if (!email || !password) {
            setFormErrors('Email and password are required');
            return;
        }

        if (!EMAIL_REGEX.test(email)) {
            setFormErrors('Please enter a valid email address');
            return;
        }

        if (password.length < 8) {
            setFormErrors('Password must be at least 8 characters long');
            return;
        }

        try {
            await login({
                ...formData,
                email,
            });

            navigate(targetRedirectPath, {
                replace: true,
            });
        } catch (err) {
            setFormErrors(err.message || 'Invalid credentials');
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
            <div className="w-full max-w-md">

                {/* Application Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg mb-4 shadow-orange-500/10">
                        <svg
                            className="w-8 h-8 text-white"
                            fill="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
                        </svg>
                    </div>

                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">
                        AISHA AI
                    </h1>

                    <p className="text-slate-400 font-medium">
                        AI Sales Assistant
                    </p>
                </div>

                {/* Login Card */}
                <div className="bg-slate-800 rounded-xl shadow-2xl border border-slate-700/60 p-8">

                    <h2 className="text-xl font-semibold text-white mb-6">
                        Welcome Back
                    </h2>

                    {/* Success Message */}
                    {successMessage && (
                        <div className="mb-5 p-3.5 bg-green-900/30 border border-green-700/40 rounded-lg">
                            <p className="text-green-400 text-sm font-medium">
                                {successMessage}
                            </p>
                        </div>
                    )}

                    {/* Error Message */}
                    {(formErrors || error) && (
                        <div className="mb-5 p-3.5 bg-red-900/30 border border-red-700/40 rounded-lg">
                            <p className="text-red-400 text-sm font-medium">
                                {formErrors || error}
                            </p>
                        </div>
                    )}

                    {/* Login Form */}
                    <form onSubmit={handleSubmit} className="space-y-4">

                        {/* Email */}
                        <div>
                            <label
                                htmlFor="email"
                                className="block text-sm font-medium text-slate-300 mb-2"
                            >
                                Email Address
                            </label>

                            <div className="relative flex items-center">
                                <Mail className="absolute right-3 w-5 h-5 text-slate-400 pointer-events-none" />

                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    disabled={loading}
                                    value={formData.email}
                                    onChange={handleChange}
                                    placeholder="you@example.com"
                                    required
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div>
                            <label
                                htmlFor="password"
                                className="block text-sm font-medium text-slate-300 mb-2"
                            >
                                Password
                            </label>

                            <div className="relative flex items-center">

                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="password"
                                    name="password"
                                    disabled={loading}
                                    value={formData.password}
                                    onChange={handleChange}
                                    placeholder="••••••••"
                                    required
                                    className="w-full px-4 py-2.5 bg-slate-700/60 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-60"
                                />

                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowPassword((prev) => !prev)
                                    }
                                    className="absolute right-3 text-slate-400 hover:text-slate-200 transition"
                                    aria-label={
                                        showPassword
                                            ? 'Hide password'
                                            : 'Show password'
                                    }
                                >
                                    {showPassword ? (
                                        <EyeOff className="w-5 h-5" />
                                    ) : (
                                        <Eye className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Login Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold py-2.5 rounded-lg hover:from-orange-600 hover:to-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition disabled:opacity-50 mt-2"
                        >
                            {loading ? 'Authenticating...' : 'Sign In'}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="my-6 relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-slate-600/80"></div>
                        </div>

                        <div className="relative flex justify-center text-sm">
                            <span className="px-3 bg-slate-800 text-slate-400 font-medium">
                                Don't have an account?
                            </span>
                        </div>
                    </div>

                    {/* Signup Link */}
                    <Link
                        to="/signup"
                        className="block w-full text-center px-4 py-2.5 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700/40 hover:border-slate-500 transition"
                    >
                        Create Account
                    </Link>

                </div>
            </div>
        </div>
    );
}