import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import (
    SessionLocal, StoreAnalysis, Product, ContactDetail, SocialHandle,
    Policy, FAQ, ImportantLink, CompetitorAnalysis, create_tables
)
from app.models.schemas import (
    BrandInsights, CompetitorAnalysis as CompetitorAnalysisSchema,
    ProductModel, ContactDetails, SocialHandles, PolicyInfo,
    FAQ as FAQSchema, ImportantLinks
)

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        # Ensure tables exist
        create_tables()

    def get_session(self) -> Session:
        """Get database session"""
        return SessionLocal()

    def save_brand_insights(self, insights: BrandInsights) -> int:
        """
        Save brand insights to database using SQLAlchemy ORM

        Args:
            insights: BrandInsights object to save

        Returns:
            int: Analysis ID of the saved record
        """
        db = self.get_session()
        try:
            # Create main analysis record
            analysis_data = {
                'brand_context': insights.brand_context,
                'errors': insights.errors,
                'extraction_metadata': {
                    'extraction_success': insights.extraction_success,
                    'extracted_at': insights.extracted_at.isoformat()
                }
            }

            db_analysis = StoreAnalysis(
                brand_name=insights.brand_name,
                website_url=insights.website_url,
                total_products=insights.total_products,
                extraction_success=insights.extraction_success,
                extracted_at=insights.extracted_at,
                analysis_data=analysis_data
            )

            db.add(db_analysis)
            db.flush()
            analysis_id = db_analysis.id

            logger.info(f"Created main analysis record with ID: {analysis_id}")

            # Save products
            self._save_products(db, analysis_id, insights.product_catalog, insights.hero_products)

            # Save contact details
            self._save_contact_details(db, analysis_id, insights.contact_details)

            # Save social handles
            self._save_social_handles(db, analysis_id, insights.social_handles)

            # Save policies
            self._save_policies(db, analysis_id, insights.policies)

            # Save FAQs
            self._save_faqs(db, analysis_id, insights.faqs)

            # Save important links
            self._save_important_links(db, analysis_id, insights.important_links)

            db.commit()
            logger.info(f"Successfully saved brand insights for {insights.brand_name}")

            return analysis_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving brand insights: {e}")
            raise
        finally:
            db.close()

    def _save_products(self, db: Session, analysis_id: int, products: List[ProductModel],
                       hero_products: List[ProductModel]):
        """Save products to database"""
        if not products:
            return

        hero_product_ids = {p.id for p in hero_products if p.id}

        for product in products:
            db_product = Product(
                analysis_id=analysis_id,
                product_id=product.id,
                title=product.title,
                handle=product.handle,
                description=product.description,
                price=float(product.price) if product.price else None,
                compare_at_price=float(product.compare_at_price) if product.compare_at_price else None,
                vendor=product.vendor,
                product_type=product.product_type,
                tags=product.tags,
                images=product.images,
                url=product.url,
                available=product.available,
                variants=product.variants,
                is_hero_product=product.id in hero_product_ids
            )
            db.add(db_product)

        logger.info(f"Saved {len(products)} products, {len(hero_product_ids)} hero products")

    def _save_contact_details(self, db: Session, analysis_id: int, contact_details: ContactDetails):
        """Save contact details to database"""
        db_contact = ContactDetail(
            analysis_id=analysis_id,
            emails=contact_details.emails,
            phone_numbers=contact_details.phone_numbers,
            address=contact_details.address,
            contact_page_url=contact_details.contact_page_url
        )
        db.add(db_contact)
        logger.info(
            f"Saved contact details: {len(contact_details.emails)} emails, {len(contact_details.phone_numbers)} phones")

    def _save_social_handles(self, db: Session, analysis_id: int, social_handles: SocialHandles):
        """Save social handles to database"""
        social_data = social_handles.model_dump()
        saved_count = 0

        for platform, url in social_data.items():
            if url:
                db_social = SocialHandle(
                    analysis_id=analysis_id,
                    platform=platform,
                    url=url
                )
                db.add(db_social)
                saved_count += 1

        logger.info(f"Saved {saved_count} social handles")

    def _save_policies(self, db: Session, analysis_id: int, policies: PolicyInfo):
        """Save policies to database"""
        policy_data = policies.model_dump()
        saved_count = 0

        for policy_type, content in policy_data.items():
            if content:
                db_policy = Policy(
                    analysis_id=analysis_id,
                    policy_type=policy_type,
                    content=content
                )
                db.add(db_policy)
                saved_count += 1

        logger.info(f"Saved {saved_count} policies")

    def _save_faqs(self, db: Session, analysis_id: int, faqs: List[FAQSchema]):
        """Save FAQs to database"""
        if not faqs:
            return

        for faq in faqs:
            db_faq = FAQ(
                analysis_id=analysis_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category
            )
            db.add(db_faq)

        logger.info(f"Saved {len(faqs)} FAQs")

    def _save_important_links(self, db: Session, analysis_id: int, important_links: ImportantLinks):
        """Save important links to database"""
        links_data = important_links.model_dump()
        saved_count = 0

        for link_type, url in links_data.items():
            if url:
                db_link = ImportantLink(
                    analysis_id=analysis_id,
                    link_type=link_type,
                    url=url
                )
                db.add(db_link)
                saved_count += 1

        logger.info(f"Saved {saved_count} important links")

    def save_competitor_analysis(self, competitor_analysis: CompetitorAnalysisSchema) -> int:
        """
        Save competitor analysis to database

        Args:
            competitor_analysis: CompetitorAnalysis object to save

        Returns:
            int: Main analysis ID
        """
        # First save the main brand analysis
        main_analysis_id = self.save_brand_insights(competitor_analysis.main_brand)

        db = self.get_session()
        try:
            # Save each competitor
            for competitor in competitor_analysis.competitors:
                # Save competitor's brand insights if available
                competitor_analysis_id = None
                if competitor.insights:
                    competitor_analysis_id = self.save_brand_insights(competitor.insights)

                # Create competitor relationship
                db_competitor = CompetitorAnalysis(
                    main_analysis_id=main_analysis_id,
                    competitor_brand_name=competitor.brand_name,
                    competitor_website_url=competitor.website_url,
                    similarity_score=float(competitor.similarity_score) if competitor.similarity_score else None,
                    competitor_analysis_id=competitor_analysis_id
                )
                db.add(db_competitor)

            db.commit()
            logger.info(f"Saved competitor analysis with {len(competitor_analysis.competitors)} competitors")

            return main_analysis_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving competitor analysis: {e}")
            raise
        finally:
            db.close()

    def get_brand_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete brand analysis by ID

        Args:
            analysis_id: ID of the analysis to retrieve

        Returns:
            Dict containing complete analysis data or None if not found
        """
        db = self.get_session()
        try:
            # Get main analysis with all relationships
            analysis = db.query(StoreAnalysis).filter(StoreAnalysis.id == analysis_id).first()

            if not analysis:
                return None

            # Build result dictionary
            result = {
                'id': analysis.id,
                'brand_name': analysis.brand_name,
                'website_url': analysis.website_url,
                'total_products': analysis.total_products,
                'extraction_success': analysis.extraction_success,
                'extracted_at': analysis.extracted_at,
                'created_at': analysis.created_at,
                'analysis_data': analysis.analysis_data,

                # Related data
                'products': [self._product_to_dict(p) for p in analysis.products],
                'hero_products': [self._product_to_dict(p) for p in analysis.products if p.is_hero_product],
                'contact_details': [self._contact_to_dict(c) for c in analysis.contact_details],
                'social_handles': [self._social_to_dict(s) for s in analysis.social_handles],
                'policies': [self._policy_to_dict(p) for p in analysis.policies],
                'faqs': [self._faq_to_dict(f) for f in analysis.faqs],
                'important_links': [self._link_to_dict(l) for l in analysis.important_links]
            }

            return result

        except Exception as e:
            logger.error(f"Error retrieving analysis {analysis_id}: {e}")
            return None
        finally:
            db.close()

    def get_competitor_analysis(self, main_analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve competitor analysis for a main brand

        Args:
            main_analysis_id: ID of the main brand analysis

        Returns:
            Dict containing competitor analysis data
        """
        db = self.get_session()
        try:
            # Get main analysis
            main_analysis = self.get_brand_analysis(main_analysis_id)
            if not main_analysis:
                return None

            # Get competitor relationships
            competitors = db.query(CompetitorAnalysis).filter(
                CompetitorAnalysis.main_analysis_id == main_analysis_id
            ).all()

            competitor_data = []
            for comp in competitors:
                competitor_info = {
                    'id': comp.id,
                    'brand_name': comp.competitor_brand_name,
                    'website_url': comp.competitor_website_url,
                    'similarity_score': float(comp.similarity_score) if comp.similarity_score else None,
                    'created_at': comp.created_at
                }

                # Add full competitor analysis if available
                if comp.competitor_analysis_id:
                    competitor_info['insights'] = self.get_brand_analysis(comp.competitor_analysis_id)

                competitor_data.append(competitor_info)

            return {
                'main_brand': main_analysis,
                'competitors': competitor_data,
                'total_competitors': len(competitor_data)
            }

        except Exception as e:
            logger.error(f"Error retrieving competitor analysis {main_analysis_id}: {e}")
            return None
        finally:
            db.close()

    def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent store analyses"""
        db = self.get_session()
        try:
            analyses = db.query(StoreAnalysis).order_by(desc(StoreAnalysis.created_at)).limit(limit).all()

            return [{
                'id': a.id,
                'brand_name': a.brand_name,
                'website_url': a.website_url,
                'total_products': a.total_products,
                'extraction_success': a.extraction_success,
                'created_at': a.created_at
            } for a in analyses]

        except Exception as e:
            logger.error(f"Error getting recent analyses: {e}")
            return []
        finally:
            db.close()

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        db = self.get_session()
        try:
            stats = {
                'total_analyses': db.query(StoreAnalysis).count(),
                'successful_analyses': db.query(StoreAnalysis).filter(StoreAnalysis.extraction_success == True).count(),
                'total_products': db.query(Product).count(),
                'total_faqs': db.query(FAQ).count(),
                'total_competitors': db.query(CompetitorAnalysis).count(),
                'recent_analyses': self.get_recent_analyses(5)
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
        finally:
            db.close()

    def search_analyses(self, brand_name: str = None, website_url: str = None) -> List[Dict[str, Any]]:
        """Search for analyses by brand name or website URL"""
        db = self.get_session()
        try:
            query = db.query(StoreAnalysis)

            if brand_name:
                query = query.filter(StoreAnalysis.brand_name.ilike(f'%{brand_name}%'))

            if website_url:
                query = query.filter(StoreAnalysis.website_url.ilike(f'%{website_url}%'))

            analyses = query.order_by(desc(StoreAnalysis.created_at)).limit(20).all()

            return [{
                'id': a.id,
                'brand_name': a.brand_name,
                'website_url': a.website_url,
                'total_products': a.total_products,
                'extraction_success': a.extraction_success,
                'created_at': a.created_at
            } for a in analyses]

        except Exception as e:
            logger.error(f"Error searching analyses: {e}")
            return []
        finally:
            db.close()

    # Helper methods to convert ORM objects to dictionaries
    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        return {
            'id': product.id,
            'product_id': product.product_id,
            'title': product.title,
            'handle': product.handle,
            'description': product.description,
            'price': float(product.price) if product.price else None,
            'compare_at_price': float(product.compare_at_price) if product.compare_at_price else None,
            'vendor': product.vendor,
            'product_type': product.product_type,
            'tags': product.tags,
            'images': product.images,
            'url': product.url,
            'available': product.available,
            'variants': product.variants,
            'is_hero_product': product.is_hero_product
        }

    def _contact_to_dict(self, contact: ContactDetail) -> Dict[str, Any]:
        return {
            'id': contact.id,
            'emails': contact.emails,
            'phone_numbers': contact.phone_numbers,
            'address': contact.address,
            'contact_page_url': contact.contact_page_url
        }

    def _social_to_dict(self, social: SocialHandle) -> Dict[str, Any]:
        return {
            'id': social.id,
            'platform': social.platform,
            'url': social.url
        }

    def _policy_to_dict(self, policy: Policy) -> Dict[str, Any]:
        return {
            'id': policy.id,
            'policy_type': policy.policy_type,
            'content': policy.content
        }

    def _faq_to_dict(self, faq: FAQ) -> Dict[str, Any]:
        return {
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'category': faq.category
        }

    def _link_to_dict(self, link: ImportantLink) -> Dict[str, Any]:
        return {
            'id': link.id,
            'link_type': link.link_type,
            'url': link.url
        }