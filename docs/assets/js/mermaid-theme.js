(() => {
  const palette = {
    background: '#0f1218',
    surface: '#161b24',
    primary: '#1dd7d4',
    primaryText: '#0f1218',
    secondary: '#c42dd2',
    secondaryText: '#f4f6fb',
    border: '#1dd7d4',
    text: '#f4f6fb'
  };

  const initMermaid = () => {
    if (!window.mermaid) {
      return;
    }

    window.mermaid.initialize({
      startOnLoad: true,
      securityLevel: 'loose',
      theme: 'base',
      themeVariables: {
        background: palette.background,
        primaryColor: palette.primary,
        primaryTextColor: palette.primaryText,
        primaryBorderColor: palette.primary,
        secondaryColor: palette.secondary,
        secondaryTextColor: palette.secondaryText,
        lineColor: palette.secondary,
        tertiaryColor: palette.surface,
        fontFamily: 'Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
        fontSize: '16px',
        clusterBkg: palette.surface,
        clusterBorder: palette.border,
        nodeTextColor: palette.text,
        edgeLabelBackground: palette.surface,
        actorBorder: palette.border,
        actorBackground: palette.surface,
        tooltipBackgroundColor: palette.surface,
        tooltipTextColor: palette.text
      }
    });
  };

  if (document.readyState !== 'loading') {
    initMermaid();
  } else {
    document.addEventListener('DOMContentLoaded', initMermaid);
  }
})();
