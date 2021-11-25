<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    version="1.0">
    <xsl:strip-space elements="*"/>
    <xsl:output method="text"/>

    <xsl:variable name="newline"><xsl:text>
</xsl:text></xsl:variable>

    <xsl:template match="/">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="tei:teiHeader">
        
    </xsl:template>

    <xsl:template match="tei:div[@type='stanza']|tei:div[@type='verse']">
        <xsl:value-of select="$newline"/>
        <xsl:text>\begin{stanza}{\</xsl:text><xsl:value-of select="substring-before(@n, '.')"/>
        <xsl:text>{</xsl:text><xsl:value-of select="substring-after(@n, '.')"/><xsl:text>}</xsl:text>
        <xsl:text>}</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>\end{stanza}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:ab[@type='ritualdirection']">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="tei:ab[@type='translation']">
        
    </xsl:template>

    <xsl:template match="tei:ab[@type='commentary']">
        
    </xsl:template>

    <xsl:template match="tei:ab[@type='verseline']|tei:ab[@type='line']">
        <xsl:apply-templates/>
    </xsl:template>
    
    <xsl:template match="tei:w[not(ancestor::tei:ab[@type='ritualdirection'])]">
        <xsl:value-of select="$newline"/>
        <xsl:text>\editedtext{</xsl:text>
        <xsl:value-of select="text()"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:w[ancestor::tei:ab[@type='ritualdirection']]">
        <xsl:value-of select="$newline"/>
        <xsl:text>\rd{</xsl:text>
        <xsl:value-of select="text()"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:lb">
        <xsl:text>\newline</xsl:text>
    </xsl:template>

    <xsl:template match="tei:pc">

    </xsl:template>

    <xsl:template match="tei:note">
        
    </xsl:template>

    <xsl:template match="tei:figure">
        
    </xsl:template>

    
</xsl:stylesheet>