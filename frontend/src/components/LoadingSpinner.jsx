/**
 * ============================================================================
 * AISHA AI - VISUAL LOADING SPINNER COMPONENT(HOLD ON A SECOND WE ARE FETCHING DATA)
 * ============================================================================
 * An accessible, highly responsive visual loader. It displays concentric,
 * counter-rotating animated rings using Tailwind CSS and handles both localized 
 * inline element rendering and full-screen loading backdrop covers.
 * 
 * @module components/LoadingSpinner
 */
 import React from 'react';

 //=====================================================
 //COMPONENT INPUTS
 //=====================================================

 export default function LoadingSpinner({ fullScreen = false, showText = true}){
    const baseClasses = 'flex flex-col sm:flex-row items-center justify-center';
   
    //=========================================================================
    //CONDITIONAL STYLING (SCREEN LAYOUT POSITION)
    //=========================================================================
    //Decide how large the container background should be depending on the screen size
    const containerClasses = fullScreen 
        ? `${baseClasses} fixed inset-0 z-50 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900`
        : `${baseClasses} py-6`;
    return(
      <div className={containerClasses} role="status" aria-live="polite">

         {/*=========================================================================
         //    SPINNING DUAL RINGS (ANIMATION LAB)
         =============================================================================*/}
         <div className="relative w-12 h-12 flex-shrink-0">
                {/* Outer ring - Fixed typo: changed inset-o to inset-0 */}
                <div className="absolute inset-0 border-4 border-slate-700 border-t-orange-500 rounded-full animate-spin"></div>
                
                {/* Inner ring - Fixed: Moved style attribute INSIDE the opening HTML tag */}
                <div 
                    className="absolute inset-2 border-2 border-slate-600 border-b-orange-500 rounded-full animate-spin"
                    style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}
                ></div>
         </div>
            <span className="sr-only">Loading...</span>
            {showText && (
        <span className="mt-3 sm:mt-0 sm:ml-4 text-slate-400 font-medium tracking-wide animate-pulse">
          Loading...
        </span>
            )}   
      </div>
         
      );
   
 }


