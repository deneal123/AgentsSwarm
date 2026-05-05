import React from "react";
import { SimpleGrid } from "@chakra-ui/react";
import { spacing } from "@theme/tokens";
import TeamMemberCard from "../TeamMemberCard";
import { MotionVStack } from "@ui/motionPrimitives";
import Section from "@ui/atoms/Section";
import SectionHeader from "@ui/atoms/SectionHeader";

function TeamSection({ members }) {
  return (
    <Section pt={{ base: 16, md: 20 }}>
      <MotionVStack
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        spacing={{ base: spacing["8xl"], md: spacing["10xl"] }}
      >
        <SectionHeader
          title="Наша команда"
          description="Вот они — бездари бигтеха слева направо:"
          align="center"
          mb={{ base: 4, md: 6 }}
        />

        <SimpleGrid
          columns={{ base: 1, md: 2, lg: 4 }}
          spacing={{ base: 8, md: 10, lg: 8 }}
          w="full"
          maxW={{ base: "full", md: "100%" }}
          pt={{ base: 4, md: 6 }}
          mx="auto"
        >
          {members.map((member, index) => (
            <TeamMemberCard key={`${member.name}-${index}`} member={member} index={index} />
          ))}
        </SimpleGrid>
      </MotionVStack>
    </Section>
  );
}

export default TeamSection;
