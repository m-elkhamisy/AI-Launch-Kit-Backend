import { Document, Page, View, Text, StyleSheet } from "@react-pdf/renderer";
import { OnboardingFormData } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import { FORM_FIELDS, SECTION_LABELS, SECTION_ORDER } from "@/lib/form-config";
import { describeFonts, describePalette } from "@/lib/design-utils";

const styles = StyleSheet.create({
  page: { padding: 40, fontSize: 10, fontFamily: "Helvetica", color: "#1a1a1a" },
  title: { fontSize: 22, marginBottom: 4, fontFamily: "Helvetica-Bold" },
  subtitle: { fontSize: 11, color: "#666", marginBottom: 20 },
  sectionTitle: {
    fontSize: 13,
    marginTop: 16,
    marginBottom: 8,
    fontFamily: "Helvetica-Bold",
    borderBottomWidth: 1,
    borderBottomColor: "#dddddd",
    paddingBottom: 4,
  },
  sectionHelp: { fontSize: 8.5, color: "#999", marginBottom: 8, fontFamily: "Helvetica-Oblique" },
  row: { marginBottom: 8 },
  label: { fontSize: 9, color: "#888", marginBottom: 2, textTransform: "uppercase", letterSpacing: 0.5 },
  value: { fontSize: 10.5, lineHeight: 1.4 },
  designRow: { flexDirection: "row", flexWrap: "wrap" },
  designItem: { width: "50%", marginBottom: 8, paddingRight: 8 },
});

interface PdfDocumentProps {
  form: OnboardingFormData;
  design?: DesignPrefs;
}

export function PdfDocument({ form, design }: PdfDocumentProps) {
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>{form.companyName || "Untitled brief"}</Text>
        <Text style={styles.subtitle}>Website brief — LaunchKit Generator</Text>

        {SECTION_ORDER.map((section) => {
          const fields = FORM_FIELDS.filter((f) => f.section === section && form[f.key]?.trim());
          if (fields.length === 0) return null;
          const meta = SECTION_LABELS[section];
          return (
            <View key={section} wrap={false}>
              <Text style={styles.sectionTitle}>{meta.title}</Text>
              {meta.helpText ? <Text style={styles.sectionHelp}>{meta.helpText}</Text> : null}
              {fields.map((f) => (
                <View key={f.key} style={styles.row}>
                  <Text style={styles.label}>{f.label}</Text>
                  <Text style={styles.value}>{form[f.key]}</Text>
                </View>
              ))}
            </View>
          );
        })}

        {design ? (
          <View wrap={false}>
            <Text style={styles.sectionTitle}>Design preferences</Text>
            <View style={styles.designRow}>
              <View style={styles.designItem}>
                <Text style={styles.label}>Style</Text>
                <Text style={styles.value}>{design.style}</Text>
              </View>
              <View style={styles.designItem}>
                <Text style={styles.label}>Color palette</Text>
                <Text style={styles.value}>{describePalette(design)}</Text>
              </View>
              <View style={styles.designItem}>
                <Text style={styles.label}>Typography</Text>
                <Text style={styles.value}>{describeFonts(design)}</Text>
              </View>
              <View style={styles.designItem}>
                <Text style={styles.label}>Animation</Text>
                <Text style={styles.value}>{design.animation}</Text>
              </View>
              {design.tagline ? (
                <View style={styles.designItem}>
                  <Text style={styles.label}>Tagline</Text>
                  <Text style={styles.value}>{design.tagline}</Text>
                </View>
              ) : null}
              {design.cta ? (
                <View style={styles.designItem}>
                  <Text style={styles.label}>Call to action</Text>
                  <Text style={styles.value}>{design.cta}</Text>
                </View>
              ) : null}
            </View>
          </View>
        ) : null}
      </Page>
    </Document>
  );
}
